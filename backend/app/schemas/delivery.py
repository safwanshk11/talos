from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PullRequestResponse(BaseModel):
    id: int
    repository_id: int
    maintenance_job_id: int
    patch_attempt_id: Optional[int] = None
    verification_run_id: Optional[int] = None
    base_branch: Optional[str] = None
    head_branch: Optional[str] = None
    commit_sha: Optional[str] = None
    title: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    status: str
    github_status: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
