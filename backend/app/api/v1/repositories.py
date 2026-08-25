from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.repository import (
    RepositoryResponse,
    ConnectRepositoryRequest,
    ToggleMonitoringRequest,
    DashboardStatsResponse,
    GitHubRepoImportItem,
    LatestCommitSchema
)
from app.services.repository_service import RepositoryService
from app.services.github_service import GitHubService

router = APIRouter()


def _to_repository_response(repo) -> RepositoryResponse:
    latest_commit = LatestCommitSchema(
        sha=repo.latest_commit_sha,
        message=repo.latest_commit_message,
        author=repo.latest_commit_author,
        date=repo.latest_commit_date
    )
    return RepositoryResponse(
        id=repo.id,
        user_id=repo.user_id,
        github_repo_id=repo.github_repo_id,
        name=repo.name,
        full_name=repo.full_name,
        owner=repo.owner,
        default_branch=repo.default_branch,
        primary_language=repo.primary_language,
        visibility=repo.visibility,
        clone_url=repo.clone_url,
        html_url=repo.html_url,
        latest_commit=latest_commit,
        monitoring_status=repo.monitoring_status,
        connection_status=repo.connection_status,
        last_checked_at=repo.last_checked_at,
        created_at=repo.created_at,
        updated_at=repo.updated_at
    )


@router.get("/available", response_model=List[GitHubRepoImportItem])
async def list_available_github_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch GitHub repositories accessible by user for importing into TALOS."""
    token = await RepositoryService.get_user_github_token(db, current_user.id)
    gh_repos = await GitHubService.fetch_user_repositories(token)

    connected_repos = await RepositoryService.list_connected_repositories(db, current_user.id)
    connected_ids = {r.github_repo_id for r in connected_repos}

    items = []
    for r in gh_repos:
        repo_id_str = str(r.get("id"))
        items.append(
            GitHubRepoImportItem(
                github_repo_id=repo_id_str,
                name=r.get("name"),
                full_name=r.get("full_name"),
                owner=r.get("owner", {}).get("login", ""),
                default_branch=r.get("default_branch", "main"),
                primary_language=r.get("language"),
                visibility="private" if r.get("private") else "public",
                clone_url=r.get("clone_url", ""),
                html_url=r.get("html_url", ""),
                description=r.get("description"),
                is_connected=(repo_id_str in connected_ids)
            )
        )
    return items


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all repositories connected to TALOS by current user."""
    repos = await RepositoryService.list_connected_repositories(db, current_user.id)
    return [_to_repository_response(r) for r in repos]


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch dashboard summary metrics backed by real database state."""
    stats = await RepositoryService.get_dashboard_stats(db, current_user.id)
    return DashboardStatsResponse(**stats)


@router.post("/connect", response_model=RepositoryResponse)
async def connect_repository(
    payload: ConnectRepositoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect a GitHub repository to TALOS for monitoring."""
    repo = await RepositoryService.connect_repository(
        db=db,
        user_id=current_user.id,
        github_repo_id=payload.github_repo_id,
        full_name=payload.full_name
    )
    return _to_repository_response(repo)


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository_detail(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information for a single connected repository."""
    repo = await RepositoryService.get_repository_by_id(db, current_user.id, repository_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    return _to_repository_response(repo)


@router.post("/{repository_id}/sync", response_model=RepositoryResponse)
async def sync_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Re-sync repository metadata and latest commit from GitHub."""
    repo = await RepositoryService.sync_repository_metadata(db, current_user.id, repository_id)
    return _to_repository_response(repo)


@router.patch("/{repository_id}/monitoring", response_model=RepositoryResponse)
async def toggle_monitoring(
    repository_id: int,
    payload: ToggleMonitoringRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle monitoring status (active / paused)."""
    repo = await RepositoryService.toggle_monitoring_status(
        db, current_user.id, repository_id, payload.monitoring_status
    )
    return _to_repository_response(repo)
