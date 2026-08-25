import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    logger.info("Database initialization complete.")
    yield
    # Shutdown
    logger.info("Shutting down TALOS Core API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TALOS Core Backend API — Autonomous Repository Maintenance System",
    version="1.0.0-phase1",
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
