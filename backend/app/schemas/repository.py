from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LatestCommitSchema(BaseModel):
    sha: Optional[str] = None
    message: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None


class GitHubRepoImportItem(BaseModel):
    github_repo_id: str
    name: str
    full_name: str
    owner: str
    default_branch: str
    primary_language: Optional[str] = None
    visibility: str
    clone_url: str
    html_url: str
    description: Optional[str] = None
    is_connected: bool = False


class ConnectRepositoryRequest(BaseModel):
    github_repo_id: str
    full_name: str


class ToggleMonitoringRequest(BaseModel):
    monitoring_status: str = Field(..., description="'active' or 'paused'")


class RepositoryResponse(BaseModel):
    id: int
    user_id: int
    github_repo_id: str
    name: str
    full_name: str
    owner: str
    default_branch: str
    primary_language: Optional[str] = None
    visibility: str
    clone_url: str
    html_url: str
    latest_commit: LatestCommitSchema
    monitoring_status: str
    connection_status: str
    last_checked_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardStatsResponse(BaseModel):
    total_repositories: int
    active_monitoring_count: int
    active_issues_count: int = 0
    verified_patches_count: int = 0
    awaiting_review_count: int = 0
