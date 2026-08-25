from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class GitHubConnectPAT(BaseModel):
    personal_access_token: str = Field(..., description="GitHub Personal Access Token (classic or fine-grained)")


class GitHubOAuthCode(BaseModel):
    code: str = Field(..., description="OAuth code returned by GitHub")


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_github_connected: bool = False
    github_username: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GitHubConnectionStatus(BaseModel):
    connected: bool
    github_username: Optional[str] = None
    connected_at: Optional[datetime] = None
    scopes: Optional[str] = None
