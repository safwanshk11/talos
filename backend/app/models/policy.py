from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base

# Sensible defaults a repository owner can add to / remove from — TALOS never
# invents these from repository content (Phase 6.5 section 43: policy comes
# only from trusted TALOS configuration, never from repository-supplied data).
DEFAULT_PROTECTED_PATHS = [
    "**/auth/**",
    "**/payments/**",
    "**/migrations/**",
    "**/infrastructure/**",
    ".github/workflows/**",
]

# Three simple presets (Phase 6.5 section 7). Major dependency updates and
# protected-path changes are never AUTO_EXECUTE in any preset — even the most
# autonomous mode preserves these as hard defaults; a repository owner may
# still loosen individual tiers via PUT /automation-policy, but the API layer
# (PolicyService.update) refuses to ever set major/protected to AUTO_EXECUTE.
POLICY_PRESETS = {
    "CONSERVATIVE": {
        "security_patch_action": "APPROVAL_REQUIRED",
        "patch_update_action": "APPROVAL_REQUIRED",
        "minor_update_action": "APPROVAL_REQUIRED",
        "major_update_action": "ESCALATE",
        "protected_path_action": "ESCALATE",
    },
    "BALANCED": {
        "security_patch_action": "AUTO_EXECUTE",
        "patch_update_action": "AUTO_EXECUTE",
        "minor_update_action": "APPROVAL_REQUIRED",
        "major_update_action": "ESCALATE",
        "protected_path_action": "APPROVAL_REQUIRED",
    },
    "AUTONOMOUS": {
        "security_patch_action": "AUTO_EXECUTE",
        "patch_update_action": "AUTO_EXECUTE",
        "minor_update_action": "AUTO_EXECUTE",
        "major_update_action": "ESCALATE",
        "protected_path_action": "APPROVAL_REQUIRED",
    },
}


class RepositoryAutomationPolicy(Base):
    """One row per repository — TALOS's Decision Engine reads this (never AI)
    to decide how far it may act autonomously on a given repository."""

    __tablename__ = "repository_automation_policies"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, unique=True)

    mode = Column(String, default="BALANCED")  # CONSERVATIVE, BALANCED, AUTONOMOUS

    # Per-tier action: AUTO_EXECUTE, PREPARE_ONLY, APPROVAL_REQUIRED, or (major/
    # protected only) ESCALATE.
    security_patch_action = Column(String, default="AUTO_EXECUTE")
    patch_update_action = Column(String, default="AUTO_EXECUTE")
    minor_update_action = Column(String, default="APPROVAL_REQUIRED")
    major_update_action = Column(String, default="ESCALATE")
    protected_path_action = Column(String, default="APPROVAL_REQUIRED")

    protected_paths = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="automation_policy")
