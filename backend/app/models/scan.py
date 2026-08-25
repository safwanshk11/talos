from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class RepositoryScan(Base):
    __tablename__ = "repository_scans"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    
    status = Column(String, default="queued")  # queued, running, completed, failed
    ecosystem = Column(String, nullable=True)  # npm, pip, etc.
    total_dependencies = Column(Integer, default=0)
    issues_detected = Column(Integer, default=0)
    
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    repository = relationship("Repository", back_populates="scans")
    action_logs = relationship("ActionLog", back_populates="scan", cascade="all, delete-orphan")
