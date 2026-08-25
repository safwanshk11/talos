from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class RepositoryReadiness(Base):
    __tablename__ = "repository_readiness"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    manifest_found = Column(Boolean, default=False)
    lockfile_found = Column(Boolean, default=False)
    build_script_found = Column(Boolean, default=False)
    test_script_found = Column(Boolean, default=False)
    lint_script_found = Column(Boolean, default=False)
    typecheck_script_found = Column(Boolean, default=False)
    ci_config_found = Column(Boolean, default=False)
    
    score_level = Column(String, default="LOW")  # HIGH, MEDIUM, LOW
    details = Column(JSON, nullable=True)

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="readiness")
