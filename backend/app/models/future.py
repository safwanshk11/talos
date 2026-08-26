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
    # OPEN, ANALYZING, PLANNING, PLANNED, SANDBOXING, PATCHING, PATCH_READY,
    # VERIFYING, VERIFIED, VERIFICATION_FAILED, DELIVERED, FAILED, ESCALATED, RESOLVED,
    # APPROVAL_REQUIRED, IGNORED, REJECTED_BY_USER (Phase 6.5: Decision Engine)
    status = Column(String, default="OPEN")
    
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
    # queued, analyzing, planning, planned, sandboxing, patching, patch_ready,
    # verifying, verified, verification_failed, delivering, delivered,
    # delivery_failed, resolved (no patch needed — already fixed upstream),
    # failed, escalated, waiting_for_approval (Phase 6.5: Decision Engine),
    # blocked_conflict, ignored, rejected
    status = Column(String, default="queued")
    risk_level = Column(String, nullable=True) # low, medium, high
    risk_reason = Column(Text, nullable=True)
    # Phase 7: provenance — manual, scheduled_scan, github_push
    trigger = Column(String, default="manual")

    # Phase 6.5: Decision Engine & Autonomy Governance — every job records the
    # decision that gated it, not just a badge: which policy was applied, which
    # deterministic rules matched, and (for BLOCKED_BY_CONFLICT) what blocked it.
    # AUTO_EXECUTE, PREPARE_ONLY, APPROVAL_REQUIRED, ESCALATE, IGNORE, BLOCKED_BY_CONFLICT
    decision = Column(String, nullable=True)
    decision_reason = Column(Text, nullable=True)
    decision_policy = Column(String, nullable=True)  # policy mode snapshot at decision time
    decision_matched_rules = Column(JSON, nullable=True)
    decision_blocked_by = Column(JSON, nullable=True)
    requires_approval = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    blocking_job_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    repository = relationship("Repository", back_populates="jobs")
    issue = relationship("MaintenanceIssue", back_populates="jobs")
    patch_attempts = relationship("PatchAttempt", back_populates="job", cascade="all, delete-orphan")
    action_logs = relationship("ActionLog", back_populates="job", cascade="all, delete-orphan")
    verification_runs = relationship("VerificationRun", back_populates="job", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequest", back_populates="job", cascade="all, delete-orphan")


class PatchAttempt(Base):
    __tablename__ = "patch_attempts"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False)
    branch_name = Column(String, nullable=False)
    base_sha = Column(String, nullable=True)  # HEAD of default branch the workspace was cloned from, before the TALOS branch/commit — needed to recompute the verified diff at delivery time
    commit_sha = Column(String, nullable=True)
    patch_diff = Column(Text, nullable=True)
    attempt_number = Column(Integer, default=1)
    status = Column(String, default="created")  # created, ready, failed, escalated, awaiting_approval

    # AI reasoning trail for this attempt
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    analysis = Column(JSON, nullable=True)          # AIProvider.analyze_problem() output
    plan = Column(JSON, nullable=True)               # AIProvider.generate_plan() output (structured plan)
    files_modified = Column(JSON, nullable=True)     # list of relative file paths actually changed
    workspace_path = Column(String, nullable=True)   # isolated clone on disk, kept for Phase 4 verification
    failure_reason = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    job = relationship("MaintenanceJob", back_populates="patch_attempts")
    verification_runs = relationship("VerificationRun", back_populates="patch_attempt", cascade="all, delete-orphan")


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id = Column(Integer, primary_key=True, index=True)
    maintenance_job_id = Column(Integer, ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=True)
    patch_attempt_id = Column(Integer, ForeignKey("patch_attempts.id", ondelete="CASCADE"), nullable=False)
    # pending, running, verified, verification_failed, failed (infrastructure), cancelled
    status = Column(String, default="pending")
    sandbox_id = Column(String, nullable=True)

    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Superseded by VerificationCheck rows below; kept unused rather than dropped
    # to avoid a destructive migration on a table with no real migration tooling.
    passed = Column(Boolean, nullable=True)
    build_passed = Column(Boolean, nullable=True)
    tests_passed = Column(Boolean, nullable=True)
    security_passed = Column(Boolean, nullable=True)
    output_log = Column(Text, nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    job = relationship("MaintenanceJob", back_populates="verification_runs")
    patch_attempt = relationship("PatchAttempt", back_populates="verification_runs")
    checks = relationship(
        "VerificationCheck",
        back_populates="verification_run",
        cascade="all, delete-orphan",
        order_by="VerificationCheck.order_index",
    )


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id = Column(Integer, primary_key=True, index=True)
    verification_run_id = Column(Integer, ForeignKey("verification_runs.id", ondelete="CASCADE"), nullable=False)

    # INSTALL, BUILD, TYPECHECK, LINT, TEST, SECURITY_AUDIT, VULNERABILITY_RESCAN
    type = Column(String, nullable=False)
    command = Column(Text, nullable=True)
    # PENDING, RUNNING, PASSED, FAILED, SKIPPED, TIMED_OUT
    status = Column(String, default="PENDING")
    exit_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    stdout_excerpt = Column(Text, nullable=True)
    stderr_excerpt = Column(Text, nullable=True)
    check_metadata = Column(JSON, nullable=True)
    order_index = Column(Integer, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    verification_run = relationship("VerificationRun", back_populates="checks")


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
    """Phase 5: one row per maintenance job's delivery attempt. `status` tracks
    TALOS's own delivery pipeline (never merges anything); `github_status`
    mirrors GitHub's real open/merged/closed state, refreshed on demand."""

    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    maintenance_job_id = Column(Integer, ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False)
    patch_attempt_id = Column(Integer, ForeignKey("patch_attempts.id", ondelete="CASCADE"), nullable=True)
    verification_run_id = Column(Integer, ForeignKey("verification_runs.id", ondelete="CASCADE"), nullable=True)

    base_branch = Column(String, nullable=True)
    head_branch = Column(String, nullable=True)
    # Superseded by head_branch; kept unused (nullable) rather than dropped so the
    # ADD COLUMN/DROP NOT NULL migration below stays valid on both fresh and
    # pre-Phase-5 databases — the same non-destructive-migration approach used
    # elsewhere in this file.
    branch_name = Column(String, nullable=True)
    commit_sha = Column(String, nullable=True)
    title = Column(String, nullable=True)

    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String, nullable=True)

    # pending, committing, pushing, creating_pr, delivered, delivery_failed, escalated
    status = Column(String, default="pending")
    # open, merged, closed — only meaningful once status == delivered
    github_status = Column(String, nullable=True)
    failure_reason = Column(Text, nullable=True)

    # SHA-256 of the diff PatchAttempt.patch_diff represents (what Phase 4 actually
    # verified) vs. of the diff freshly recomputed from the workspace immediately
    # before push. Delivery is blocked unless these match.
    verification_artifact_hash = Column(String, nullable=True)
    delivery_artifact_hash = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="pull_requests")
    job = relationship("MaintenanceJob", back_populates="pull_requests")
