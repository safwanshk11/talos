from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict


class VerificationCheckResponse(BaseModel):
    id: int
    verification_run_id: int
    type: str
    command: Optional[str] = None
    status: str
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    stdout_excerpt: Optional[str] = None
    stderr_excerpt: Optional[str] = None
    check_metadata: Optional[Dict[str, Any]] = None
    order_index: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VerificationRunResponse(BaseModel):
    id: int
    maintenance_job_id: Optional[int] = None
    patch_attempt_id: int
    status: str
    sandbox_id: Optional[str] = None
    executor: Optional[str] = None
    external_run_url: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    checks: List[VerificationCheckResponse] = []

    model_config = ConfigDict(from_attributes=True)


class WorkerCallbackCheckResult(BaseModel):
    """One check's outcome as reported by a GitHub Actions runner."""
    type: str
    command: Optional[str] = None
    status: str  # PASSED, FAILED, TIMED_OUT, SKIPPED
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    stdout_excerpt: Optional[str] = None
    stderr_excerpt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkerCallbackRequest(BaseModel):
    checks: List[WorkerCallbackCheckResult]
    external_run_url: Optional[str] = None
