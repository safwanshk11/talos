from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_healthy = True
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_healthy = False
        db_status = f"unhealthy: {str(e)}"

    body = {
        "status": "ok" if db_healthy else "degraded",
        "service": "TALOS Core API",
        "database": db_status,
        "version": "1.0.0-phase9",
        # Read-only traceability — never expose secrets (GEMINI_API_KEY etc.) here.
        "ai_provider": settings.AI_PROVIDER,
        "ai_model": settings.AI_MODEL,
    }
    # A non-200 status here is what lets Docker's HEALTHCHECK (and any future
    # load balancer) actually detect a broken database connection — a 200
    # with "unhealthy" buried in the JSON body is invisible to both.
    return JSONResponse(content=body, status_code=200 if db_healthy else 503)
