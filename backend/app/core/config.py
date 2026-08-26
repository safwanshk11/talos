import logging
import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("talos.config")

DEFAULT_SECRET_KEY = "talos-super-secret-key-change-in-production-32-chars-minimum"


class Settings(BaseSettings):
    PROJECT_NAME: str = "TALOS"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "talos"
    POSTGRES_PASSWORD: str = "talos_secret_pass"
    POSTGRES_DB: str = "talos_db"
    DATABASE_URL: Union[str, None] = None

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"
    GITHUB_PERSONAL_ACCESS_TOKEN: str = ""

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]

    # AI Provider (Phase 3: Planning & Patch Generation)
    # "ollama" for local/dev reasoning, "gemini" for deployment.
    AI_PROVIDER: str = "ollama"
    AI_MODEL: str = "qwen2.5:7b"
    AI_TIMEOUT_SECONDS: int = 180
    AI_MAX_RETRIES: int = 2

    OLLAMA_BASE_URL: str = "http://localhost:11434"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Continuous Monitoring (Phase 7)
    GITHUB_WEBHOOK_SECRET: str = ""
    MONITORING_SCHEDULER_INTERVAL_MINUTES: int = 15
    MONITORING_SCHEDULER_ENABLED: bool = True

    # Verification Engine (Phase 4)
    VERIFICATION_SANDBOX_IMAGE_NPM: str = "node:20-slim"
    VERIFICATION_SANDBOX_IMAGE_PIP: str = "python:3.11-slim"
    VERIFICATION_TIMEOUT_INSTALL: int = 180
    VERIFICATION_TIMEOUT_BUILD: int = 180
    VERIFICATION_TIMEOUT_TEST: int = 180
    VERIFICATION_TIMEOUT_DEFAULT: int = 120
    VERIFICATION_MEMORY_LIMIT: str = "1g"
    VERIFICATION_CPU_LIMIT: str = "1.5"

    # Production Hardening (Phase 8)
    # How long a completed job's patch workspace survives on disk before the
    # reaper reclaims it (see monitoring_service.WorkspaceReaperService).
    WORKSPACE_RETENTION_HOURS: int = 24

    # Verification Execution Adapter (Phase 10). "docker" (default) runs the
    # existing local docker-outside-of-docker sandbox. "github_actions" is for
    # deployments (e.g. Render) with no Docker socket available — it dispatches
    # a workflow_dispatch run on GITHUB_ACTIONS_REPO and waits for a signed
    # callback. Explicit and independent of ENVIRONMENT on purpose: flipping
    # ENVIRONMENT=production shouldn't silently also change how verification
    # executes — a deployment WITH Docker access should be free to keep using
    # the local sandbox in production.
    VERIFICATION_EXECUTOR: str = "docker"
    # "<owner>/<repo>" hosting .github/workflows/talos-verification.yml —
    # normally TALOS's own repository, not the repository being verified.
    GITHUB_ACTIONS_REPO: str = ""
    GITHUB_ACTIONS_WORKFLOW_FILE: str = "talos-verification.yml"
    GITHUB_ACTIONS_REF: str = "main"
    # This backend's own publicly reachable base URL, so the dispatched
    # workflow knows where to POST its callback. Not a secret.
    TALOS_API_URL: str = ""
    # Shared secret authenticating the callback FROM the GitHub Actions runner
    # TO this backend — a completely different credential from SECRET_KEY
    # (which signs user sessions) and never handed to repository code.
    TALOS_WORKER_SECRET: str = ""

    @property
    def sync_database_url(self) -> str:
        """Returns synchronous database URL for Alembic migrations if needed."""
        async_url = self.get_database_url()
        return async_url.replace("postgresql+asyncpg://", "postgresql://")

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()


class ConfigurationError(Exception):
    """Raised at startup when configuration is unsafe or unusable — never at
    the moment a user starts a maintenance job (Phase 8 section 6)."""


def validate_startup_config() -> None:
    """Fail fast on configuration that would otherwise surface as a confusing
    failure deep inside a scan/patch/webhook request. In production
    (ENVIRONMENT=production) unsafe defaults are fatal; in development they
    only log a warning so the existing local workflow keeps working."""
    is_production = settings.ENVIRONMENT.lower() == "production"
    errors: List[str] = []
    warnings: List[str] = []

    if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        msg = "SECRET_KEY is still the published default — JWTs can be forged by anyone who reads this repo."
        (errors if is_production else warnings).append(msg)

    if settings.AI_PROVIDER not in ("ollama", "gemini"):
        errors.append(f"AI_PROVIDER={settings.AI_PROVIDER!r} is not a supported provider (expected 'ollama' or 'gemini').")
    elif settings.AI_PROVIDER == "gemini" and not settings.GEMINI_API_KEY:
        msg = "AI_PROVIDER=gemini but GEMINI_API_KEY is not set — every AI-driven analysis/plan/patch call will fail."
        (errors if is_production else warnings).append(msg)

    if not settings.GITHUB_WEBHOOK_SECRET:
        warnings.append("GITHUB_WEBHOOK_SECRET is not set — inbound GitHub webhooks will be rejected until it is configured.")

    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        warnings.append("GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET are not set — GitHub OAuth login will be unavailable (personal access token login still works).")

    if is_production and "localhost" in settings.GITHUB_REDIRECT_URI:
        warnings.append(f"GITHUB_REDIRECT_URI still points at localhost ({settings.GITHUB_REDIRECT_URI}) in a production environment.")

    if is_production and any("localhost" in origin for origin in settings.BACKEND_CORS_ORIGINS):
        warnings.append("BACKEND_CORS_ORIGINS still includes localhost origins in a production environment.")

    if settings.VERIFICATION_EXECUTOR not in ("docker", "github_actions"):
        errors.append(f"VERIFICATION_EXECUTOR={settings.VERIFICATION_EXECUTOR!r} is not supported (expected 'docker' or 'github_actions').")
    elif settings.VERIFICATION_EXECUTOR == "github_actions":
        missing = [
            name for name, val in [
                ("GITHUB_ACTIONS_REPO", settings.GITHUB_ACTIONS_REPO),
                ("TALOS_API_URL", settings.TALOS_API_URL),
                ("TALOS_WORKER_SECRET", settings.TALOS_WORKER_SECRET),
            ] if not val
        ]
        if missing:
            errors.append(f"VERIFICATION_EXECUTOR=github_actions requires {', '.join(missing)} to be set.")

    for w in warnings:
        logger.warning(f"[config] {w}")

    if errors:
        for e in errors:
            logger.error(f"[config] {e}")
        raise ConfigurationError(
            f"{len(errors)} fatal configuration error(s) in a production environment: " + " | ".join(errors)
        )
