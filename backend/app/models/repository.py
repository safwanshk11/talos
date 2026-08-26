from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    github_repo_id = Column(String, index=True, nullable=False)
    
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False, index=True)
    owner = Column(String, nullable=False)
    default_branch = Column(String, default="main")
    primary_language = Column(String, nullable=True)
    visibility = Column(String, default="public")  # public, private
    clone_url = Column(String, nullable=False)
    html_url = Column(String, nullable=False)

    # Latest commit tracking
    latest_commit_sha = Column(String, nullable=True)
    latest_commit_message = Column(Text, nullable=True)
    latest_commit_author = Column(String, nullable=True)
    latest_commit_date = Column(DateTime(timezone=True), nullable=True)

    # Monitoring & Status
    monitoring_status = Column(String, default="active")  # active, paused
    connection_status = Column(String, default="connected")  # connected, error, syncing
    last_checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 7: Continuous Autonomous Monitoring. Defaults to "manual" rather than
    # the spec's suggested "daily" default — this connects to real, already-live
    # GitHub repositories, and a newly-shipped background scheduler should not
    # start autonomously scanning/patching them without the owner opting in per
    # repository. scan_on_relevant_push is harmless at "True" by default since it
    # can only ever fire from a webhook GitHub delivers to a URL the owner
    # explicitly configured — nothing here can trigger it on its own.
    monitoring_schedule = Column(String, default="manual")  # manual, daily, weekly
    scan_on_relevant_push = Column(Boolean, default=True)
    last_automatic_scan_at = Column(DateTime(timezone=True), nullable=True)
    last_trigger = Column(String, nullable=True)  # manual, scheduled_scan, github_push

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="repositories")

    # Relationships
    issues = relationship("MaintenanceIssue", back_populates="repository", cascade="all, delete-orphan")
    jobs = relationship("MaintenanceJob", back_populates="repository", cascade="all, delete-orphan")
    scans = relationship("RepositoryScan", back_populates="repository", cascade="all, delete-orphan")
    dependencies = relationship("Dependency", back_populates="repository", cascade="all, delete-orphan")
    readiness = relationship("RepositoryReadiness", back_populates="repository", uselist=False, cascade="all, delete-orphan")
    action_logs = relationship("ActionLog", back_populates="repository", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequest", back_populates="repository", cascade="all, delete-orphan")
    automation_policy = relationship("RepositoryAutomationPolicy", back_populates="repository", uselist=False, cascade="all, delete-orphan")
    events = relationship("RepositoryEvent", back_populates="repository", cascade="all, delete-orphan")
