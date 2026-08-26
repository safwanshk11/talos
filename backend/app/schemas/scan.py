from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict


class RepositoryScanResponse(BaseModel):
    id: int
    repository_id: int
    status: str
    ecosystem: Optional[str] = None
    total_dependencies: int = 0
    issues_detected: int = 0
    trigger: Optional[str] = "manual"
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MaintenanceIssueResponse(BaseModel):
    id: int
    repository_id: int
    fingerprint: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    category: str
    status: str
    package_name: Optional[str] = None
    current_version: Optional[str] = None
    affected_range: Optional[str] = None
    recommended_version: Optional[str] = None
    advisory_id: Optional[str] = None
    source: Optional[str] = None
    affected_files: Optional[List[str]] = []
    details: Optional[Dict[str, Any]] = None
    detected_at: datetime
    last_seen_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RepositoryReadinessResponse(BaseModel):
    id: int
    repository_id: int
    manifest_found: bool
    lockfile_found: bool
    build_script_found: bool
    test_script_found: bool
    lint_script_found: bool
    typecheck_script_found: bool
    ci_config_found: bool
    score_level: str
    details: Optional[Dict[str, Any]] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionLogResponse(BaseModel):
    id: int
    repository_id: Optional[int] = None
    scan_id: Optional[int] = None
    job_id: Optional[int] = None
    timestamp: datetime
    step: str
    message: str
    level: str

    model_config = ConfigDict(from_attributes=True)
