import hmac
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import get_db
from app.models.future import MaintenanceJob, MaintenanceIssue, PatchAttempt, VerificationRun, VerificationCheck
from app.models.repository import Repository
from app.schemas.verification import WorkerCallbackRequest
from app.services.verification.verification_service import VerificationService

logger = logging.getLogger("talos.verification.callback")
router = APIRouter()


async def verify_worker_secret(x_talos_worker_secret: str = Header(default="")) -> None:
    """Authenticates a callback as genuinely coming from a TALOS-dispatched
    GitHub Actions run — a completely different credential from user JWTs
    (get_current_user) and never handed to repository code. Constant-time
    compare, same reasoning as the GitHub webhook signature check."""
    if not settings.TALOS_WORKER_SECRET:
        raise HTTPException(status_code=503, detail="TALOS_WORKER_SECRET is not configured; callbacks are refused.")
    if not x_talos_worker_secret or not hmac.compare_digest(x_talos_worker_secret, settings.TALOS_WORKER_SECRET):
        raise HTTPException(status_code=401, detail="Invalid worker secret.")


@router.post("/verification/{verification_run_id}/callback")
async def verification_callback(
    verification_run_id: int,
    payload: WorkerCallbackRequest,
    _auth: None = Depends(verify_worker_secret),
    db: AsyncSession = Depends(get_db),
):
    """Where a GitHub Actions runner reports real check results back for a
    verification TALOS dispatched (VERIFICATION_EXECUTOR=github_actions).
    Applies the exact same VERIFIED/VERIFICATION_FAILED verdict logic the
    local Docker path uses — this endpoint decides nothing on its own about
    what counts as a pass."""
    run = (await db.execute(select(VerificationRun).where(VerificationRun.id == verification_run_id))).scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Verification run not found.")

    if run.status != "running":
        # Idempotent no-op — GitHub Actions may retry a callback delivery
        # (e.g. a transient network error on its side), and a run can only be
        # finalized once. Never re-finalize, and never re-trigger delivery.
        return {"status": "ignored", "reason": f"verification run is already '{run.status}'"}

    job = (await db.execute(select(MaintenanceJob).where(MaintenanceJob.id == run.maintenance_job_id))).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Maintenance job for this verification run not found.")
    issue = None
    if job.issue_id:
        issue = (await db.execute(select(MaintenanceIssue).where(MaintenanceIssue.id == job.issue_id))).scalars().first()
    attempt = (await db.execute(select(PatchAttempt).where(PatchAttempt.id == run.patch_attempt_id))).scalars().first()
    repo = (await db.execute(select(Repository).where(Repository.id == job.repository_id))).scalars().first()
    if not attempt or not repo:
        raise HTTPException(status_code=404, detail="Patch attempt or repository for this verification run not found.")

    if payload.external_run_url:
        run.external_run_url = payload.external_run_url
        await db.commit()

    # Update the PENDING rows the GitHubActionsVerificationExecutor
    # pre-created (so the UI showed real progress while the runner worked)
    # rather than inserting duplicates.
    existing_by_type = {
        c.type: c for c in (
            await db.execute(select(VerificationCheck).where(VerificationCheck.verification_run_id == run.id))
        ).scalars().all()
    }

    for reported in payload.checks:
        row = existing_by_type.get(reported.type)
        if row is None:
            row = VerificationCheck(verification_run_id=run.id, type=reported.type, order_index=len(existing_by_type) + 1)
            db.add(row)
            existing_by_type[reported.type] = row
        row.command = reported.command
        row.status = reported.status
        row.exit_code = reported.exit_code
        row.duration_ms = reported.duration_ms
        row.stdout_excerpt = reported.stdout_excerpt
        row.stderr_excerpt = reported.stderr_excerpt
        row.check_metadata = reported.metadata
        row.completed_at = datetime.now(timezone.utc)
    await db.commit()

    ecosystem = VerificationService._detect_ecosystem(attempt.workspace_path) if attempt.workspace_path else "unknown"
    await VerificationService._finalize_after_checks(db, run, job, issue, repo, attempt, ecosystem)

    # Resume the same auto-chain a synchronous Docker verification would have
    # continued through inline — the callback is the only place left that can
    # do this for a dispatched run (see patch_service._auto_chain).
    await db.refresh(job)
    if run.status == "verified" and job.decision == "AUTO_EXECUTE":
        try:
            from app.services.delivery_service import DeliveryService
            from app.services.repository_service import RepositoryService

            token = await RepositoryService.get_user_github_token(db, repo.user_id)
            await VerificationService._log(
                db, job.id, repo.id, "DELIVER",
                "Autonomous execution: GitHub Actions verification passed, proceeding directly to delivery.",
            )
            await DeliveryService.deliver(db, repo.user_id, repo.id, job.id, token)
        except Exception as exc:
            logger.warning(f"Auto-chain delivery did not complete for job {job.id} after GitHub Actions callback: {exc}")

    return {"status": "recorded", "verification_run_status": run.status}
