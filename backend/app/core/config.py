import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TALOS"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str = "talos-super-secret-key-change-in-production-32-chars-minimum"
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
