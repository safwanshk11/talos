from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base


class MaintenanceIssue(Base):
    __tablename__ = "maintenance_issues"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    
    # Issue Fingerprint for Deduplication
    fingerprint = Column(String, index=True, nullable=True)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String, default="MEDIUM")  # CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
    category = Column(String, default="vulnerability") # vulnerability, outdated_dependency, ci_failure, deprecated_api
    status = Column(String, default="OPEN") # OPEN, ANALYZING, PATCHING, VERIFIED, DELIVERED, FAILED, ESCALATED, RESOLVED
    
    # Vulnerability Specific Metadata
    package_name = Column(String, index=True, nullable=True)
    current_version = Column(String, nullable=True)
    affected_range = Column(String, nullable=True)
    recommended_version = Column(String, nullable=True)
    advisory_id = Column(String, nullable=True)
    source = Column(String, default="npm-audit")  # npm-audit, osv, PyPI
    
    # List of relative file paths referencing this vulnerable package
    affected_files = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)

    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="issues")
    jobs = relationship("MaintenanceJob", back_populates="issue", cascade="all, delete-orphan")


class MaintenanceJob(Base):
    __tablename__ = "maintenance_jobs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    issue_id = Column(Integer, ForeignKey("maintenance_issues.id", ondelete="CASCADE"), nullable=True)
    status = Column(String, default="queued") # queued, running, passed, failed, escalated
    risk_level = Column(String, default="low") # low, medium, high
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    repository = relationship("Repository", back_populates="jobs")
    issue = relationship("MaintenanceIssue", back_populates="jobs")
    patch_attempts = relationship("PatchAttempt", back_populates="job", cascade="all, delete-orphan")
    action_logs = relationship("ActionLog", back_populates="job", cascade="all, delete-orphan")


class PatchAttempt(Base):
    __tablename__ = "patch_attempts"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False)
    branch_name = Column(String, nullable=False)
    commit_sha = Column(String, nullable=True)
    patch_diff = Column(Text, nullable=True)
    attempt_number = Column(Integer, default=1)
    status = Column(String, default="created")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    job = relationship("MaintenanceJob", back_populates="patch_attempts")
    verification_runs = relationship("VerificationRun", back_populates="patch_attempt", cascade="all, delete-orphan")


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id = Column(Integer, primary_key=True, index=True)
    patch_attempt_id = Column(Integer, ForeignKey("patch_attempts.id", ondelete="CASCADE"), nullable=False)
    passed = Column(Boolean, default=False)
    build_passed = Column(Boolean, nullable=True)
    tests_passed = Column(Boolean, nullable=True)
    security_passed = Column(Boolean, nullable=True)
    output_log = Column(Text, nullable=True)

    executed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patch_attempt = relationship("PatchAttempt", back_populates="verification_runs")


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True)
    job_id = Column(Integer, ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=True)
    scan_id = Column(Integer, ForeignKey("repository_scans.id", ondelete="CASCADE"), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    step = Column(String, nullable=False) # WATCH, DETECT, UNDERSTAND, PLAN, PATCH, VERIFY, DELIVER, ESCALATE
    message = Column(Text, nullable=False)
    level = Column(String, default="INFO")

    job = relationship("MaintenanceJob", back_populates="action_logs")
    scan = relationship("RepositoryScan", back_populates="action_logs")
    repository = relationship("Repository", back_populates="action_logs")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    pr_number = Column(Integer, nullable=False)
    pr_url = Column(String, nullable=False)
    branch_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default="open") # open, merged, closed

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
