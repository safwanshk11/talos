from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
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
