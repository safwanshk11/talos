import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings, validate_startup_config
from app.db.session import engine
from app.db.base import Base
from app.api.v1 import health, auth, repositories, webhooks
from app.api.internal import verification_callback
from app.services.monitoring_service import SchedulerService

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("talos")


async def _scheduler_loop():
    """Phase 7: the simplest deployment-compatible scheduler — an asyncio task
    inside this same backend process (see monitoring_service.SchedulerService).
    No new worker/queue infrastructure. A failure in one tick is logged and
    never crashes the loop."""
    interval_seconds = max(60, settings.MONITORING_SCHEDULER_INTERVAL_MINUTES * 60)
    while True:
        try:
            await SchedulerService.tick()
        except Exception:
            logger.exception("Monitoring scheduler tick failed.")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate configuration before touching the database at all —
    # a misconfigured deployment should fail loudly here, not three requests
    # later inside a scan or patch job (Phase 8 section 6).
    validate_startup_config()

    # Startup: create tables if they do not exist
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(
            "ALTER TABLE repositories ADD COLUMN IF NOT EXISTS last_scanned_at "
            "TIMESTAMP WITH TIME ZONE"
        ))
        # Pre-existing action_logs tables predate repository_id/scan_id being added to
        # the model, and had job_id as NOT NULL — this silently broke every ledger
        # write from Phase 2 scans (which log with job_id=NULL). Patch it in place.
        await conn.execute(text(
            "ALTER TABLE action_logs ADD COLUMN IF NOT EXISTS repository_id INTEGER"
        ))
        await conn.execute(text(
            "ALTER TABLE action_logs ADD COLUMN IF NOT EXISTS scan_id INTEGER"
        ))
        await conn.execute(text(
            "ALTER TABLE action_logs ALTER COLUMN job_id DROP NOT NULL"
        ))

        # Same drift on maintenance_issues — it predates the vulnerability-specific
        # columns (fingerprint, package_name, etc.) added to the model during
        # Phase 2, so every scan's issue upsert has been failing silently.
        for column, coltype in [
            ("fingerprint", "VARCHAR"),
            ("package_name", "VARCHAR"),
            ("current_version", "VARCHAR"),
            ("affected_range", "VARCHAR"),
            ("recommended_version", "VARCHAR"),
            ("advisory_id", "VARCHAR"),
            ("source", "VARCHAR"),
            ("affected_files", "JSON"),
            ("detected_at", "TIMESTAMP WITH TIME ZONE"),
            ("last_seen_at", "TIMESTAMP WITH TIME ZONE"),
            ("resolved_at", "TIMESTAMP WITH TIME ZONE"),
        ]:
            await conn.execute(text(
                f"ALTER TABLE maintenance_issues ADD COLUMN IF NOT EXISTS {column} {coltype}"
            ))

        # Phase 3: Planning & Patch Generation columns added to pre-existing tables.
        await conn.execute(text(
            "ALTER TABLE maintenance_jobs ADD COLUMN IF NOT EXISTS risk_reason TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS ai_provider VARCHAR"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS ai_model VARCHAR"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS analysis JSON"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS plan JSON"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS files_modified JSON"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS workspace_path VARCHAR"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS failure_reason TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE"
        ))
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE"
        ))

        # Phase 4: Verification Engine — verification_runs predates this phase's
        # columns (only had patch_attempt_id + the old boolean summary fields).
        for column, coltype in [
            ("maintenance_job_id", "INTEGER"),
            ("status", "VARCHAR"),
            ("sandbox_id", "VARCHAR"),
            ("started_at", "TIMESTAMP WITH TIME ZONE"),
            ("completed_at", "TIMESTAMP WITH TIME ZONE"),
        ]:
            await conn.execute(text(
                f"ALTER TABLE verification_runs ADD COLUMN IF NOT EXISTS {column} {coltype}"
            ))

        # Phase 5: GitHub Delivery & Pull Requests.
        await conn.execute(text(
            "ALTER TABLE patch_attempts ADD COLUMN IF NOT EXISTS base_sha VARCHAR"
        ))
        # pull_requests predates Phase 5's real columns (only had the earlier
        # placeholder shape: repository_id, pr_number, pr_url, branch_name, title,
        # status, created_at — all required). Widen the old required columns and
        # add the new ones non-destructively rather than dropping the table.
        for column in ("branch_name", "pr_number", "pr_url", "title"):
            await conn.execute(text(
                f"ALTER TABLE pull_requests ALTER COLUMN {column} DROP NOT NULL"
            ))
        for column, coltype in [
            ("maintenance_job_id", "INTEGER"),
            ("patch_attempt_id", "INTEGER"),
            ("verification_run_id", "INTEGER"),
            ("base_branch", "VARCHAR"),
            ("head_branch", "VARCHAR"),
            ("commit_sha", "VARCHAR"),
            ("github_status", "VARCHAR"),
            ("failure_reason", "TEXT"),
            ("verification_artifact_hash", "VARCHAR"),
            ("delivery_artifact_hash", "VARCHAR"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE"),
        ]:
            await conn.execute(text(
                f"ALTER TABLE pull_requests ADD COLUMN IF NOT EXISTS {column} {coltype}"
            ))

        # Phase 6.5: Decision Engine & Autonomy Governance — decision fields added
        # to the pre-existing maintenance_jobs table (repository_automation_policies
        # is a brand-new table, already handled by create_all above).
        for column, coltype in [
            ("decision", "VARCHAR"),
            ("decision_reason", "TEXT"),
            ("decision_policy", "VARCHAR"),
            ("decision_matched_rules", "JSON"),
            ("decision_blocked_by", "JSON"),
            ("requires_approval", "BOOLEAN DEFAULT FALSE"),
            ("approved_at", "TIMESTAMP WITH TIME ZONE"),
            ("rejected_at", "TIMESTAMP WITH TIME ZONE"),
            ("rejection_reason", "TEXT"),
            ("blocking_job_id", "INTEGER"),
        ]:
            await conn.execute(text(
                f"ALTER TABLE maintenance_jobs ADD COLUMN IF NOT EXISTS {column} {coltype}"
            ))

        # Phase 7: Continuous Autonomous Monitoring — monitoring config added to
        # repositories; provenance columns added to maintenance_jobs/repository_scans
        # (repository_events is a brand-new table, already handled by create_all above).
        for column, coltype in [
            ("monitoring_schedule", "VARCHAR DEFAULT 'manual'"),
            ("scan_on_relevant_push", "BOOLEAN DEFAULT TRUE"),
            ("last_automatic_scan_at", "TIMESTAMP WITH TIME ZONE"),
            ("last_trigger", "VARCHAR"),
        ]:
            await conn.execute(text(
                f"ALTER TABLE repositories ADD COLUMN IF NOT EXISTS {column} {coltype}"
            ))
        await conn.execute(text(
            "ALTER TABLE maintenance_jobs ADD COLUMN IF NOT EXISTS trigger VARCHAR DEFAULT 'manual'"
        ))
        await conn.execute(text(
            "ALTER TABLE repository_scans ADD COLUMN IF NOT EXISTS trigger VARCHAR DEFAULT 'manual'"
        ))

        # Phase 10: Verification Execution Adapter — which VerificationExecutor
        # actually ran a given run (docker/github_actions), and the GitHub
        # Actions run's own URL when applicable.
        await conn.execute(text(
            "ALTER TABLE verification_runs ADD COLUMN IF NOT EXISTS executor VARCHAR DEFAULT 'docker'"
        ))
        await conn.execute(text(
            "ALTER TABLE verification_runs ADD COLUMN IF NOT EXISTS external_run_url VARCHAR"
        ))

        # Phase 7 section 43 (Durable Work): a scan/job left mid-flight by a
        # process restart (crash, redeploy) would otherwise sit in a "running"/
        # "active" state forever — and Phase 7's own concurrency locks
        # (has_active_scan / has_active_job) would then treat that repository
        # as permanently busy, silently blocking all future autonomous work.
        # Reconcile on every startup: mark them failed and diagnosable rather
        # than pretending exactly-once execution survived a restart it didn't.
        await conn.execute(text(
            "UPDATE maintenance_issues SET status = 'FAILED' "
            "WHERE status IN ('ANALYZING','PLANNING','PLANNED','SANDBOXING','PATCHING','VERIFYING','DELIVERING') "
            "AND id IN ("
            "  SELECT issue_id FROM maintenance_jobs "
            "  WHERE status IN ('analyzing','planning','planned','sandboxing','patching','verifying','delivering') "
            "  AND issue_id IS NOT NULL"
            ")"
        ))
        await conn.execute(text(
            "UPDATE maintenance_jobs SET status = 'failed', completed_at = NOW() "
            "WHERE status IN ('analyzing','planning','planned','sandboxing','patching','verifying','delivering')"
        ))
        await conn.execute(text(
            "UPDATE repository_scans SET status = 'failed', error_message = 'Interrupted by server restart.', completed_at = NOW() "
            "WHERE status IN ('queued','running')"
        ))
    logger.info("Database initialization complete.")

    scheduler_task = None
    if settings.MONITORING_SCHEDULER_ENABLED:
        scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info(f"Monitoring scheduler started (interval={settings.MONITORING_SCHEDULER_INTERVAL_MINUTES}m).")

    yield
    # Shutdown
    if scheduler_task:
        scheduler_task.cancel()
    logger.info("Shutting down TALOS Core API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TALOS Core Backend API — Autonomous Repository Maintenance System",
    version="1.0.0-phase9",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth & GitHub"])
app.include_router(repositories.router, prefix="/api/v1/repositories", tags=["Repositories"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(verification_callback.router, prefix="/api/internal", tags=["Internal — Verification Worker Callback"])


@app.get("/")
async def root():
    return {
        "app": "TALOS",
        "tagline": "Autonomous Repository Maintenance System",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
