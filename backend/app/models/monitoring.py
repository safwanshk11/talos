from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class RepositoryEvent(Base):
    """Phase 7: a normalized record of one inbound trigger — a GitHub webhook
    delivery or an internal scheduled-scan tick. This is the audit trail that
    answers "what triggered this?" for every autonomous run (section 53)."""

    __tablename__ = "repository_events"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True)

    provider = Column(String, default="github")
    event_type = Column(String, nullable=False)  # push, pull_request, scheduled_scan
    # GitHub's X-GitHub-Delivery header — the idempotency key. NULL for internally
    # generated events (scheduled ticks), which have no external delivery id.
    delivery_id = Column(String, index=True, nullable=True)

    branch = Column(String, nullable=True)
    commit_sha = Column(String, nullable=True)

    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # received, processed, skipped, failed
    status = Column(String, default="received")
    skip_reason = Column(String, nullable=True)
    triggered_scan_id = Column(Integer, ForeignKey("repository_scans.id", ondelete="SET NULL"), nullable=True)

    # Bounded, deliberately small — never the raw webhook payload (section 15/52).
    event_metadata = Column(JSON, nullable=True)

    repository = relationship("Repository", back_populates="events")
