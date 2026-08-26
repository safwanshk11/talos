from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class RepositoryEventResponse(BaseModel):
    id: int
    repository_id: Optional[int] = None
    provider: str
    event_type: str
    delivery_id: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    received_at: datetime
    processed_at: Optional[datetime] = None
    status: str
    skip_reason: Optional[str] = None
    triggered_scan_id: Optional[int] = None
    event_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
