from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict


class PatchAttemptResponse(BaseModel):
    id: int
    job_id: int
    attempt_number: int
    branch_name: str
    commit_sha: Optional[str] = None
    status: str
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    files_modified: Optional[List[str]] = None
    patch_diff: Optional[str] = None
    failure_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenanceJobResponse(BaseModel):
    id: int
    repository_id: int
    issue_id: Optional[int] = None
    status: str
    risk_level: Optional[str] = None
    risk_reason: Optional[str] = None

    # Phase 6.5: Decision Engine & Autonomy Governance
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decision_policy: Optional[str] = None
    decision_matched_rules: Optional[List[str]] = None
    decision_blocked_by: Optional[List[str]] = None
    requires_approval: bool = False
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    blocking_job_id: Optional[int] = None

    created_at: datetime
    completed_at: Optional[datetime] = None
    attempts: List[PatchAttemptResponse] = []

    model_config = ConfigDict(from_attributes=True)
