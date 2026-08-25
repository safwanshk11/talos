import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from app.api.v1 import health, auth, repositories

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("talos")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    logger.info("Database initialization complete.")
    yield
    # Shutdown
    logger.info("Shutting down TALOS Core API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TALOS Core Backend API — Autonomous Repository Maintenance System",
    version="1.0.0-phase3",
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


@app.get("/")
async def root():
    return {
        "app": "TALOS",
        "tagline": "Autonomous Repository Maintenance System",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
