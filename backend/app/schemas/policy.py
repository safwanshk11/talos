from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class AutomationPolicyResponse(BaseModel):
    id: int
    repository_id: int
    mode: str
    security_patch_action: str
    patch_update_action: str
    minor_update_action: str
    major_update_action: str
    protected_path_action: str
    protected_paths: List[str] = []
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UpdateAutomationPolicyRequest(BaseModel):
    mode: Optional[str] = None
    security_patch_action: Optional[str] = None
    patch_update_action: Optional[str] = None
    minor_update_action: Optional[str] = None
    major_update_action: Optional[str] = None
    protected_path_action: Optional[str] = None
    protected_paths: Optional[List[str]] = None


class RejectJobRequest(BaseModel):
    reason: Optional[str] = None
