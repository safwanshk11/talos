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
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    checks: List[VerificationCheckResponse] = []

    model_config = ConfigDict(from_attributes=True)
