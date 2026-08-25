from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.repository import Repository
from app.models.github import GitHubConnection
from app.models.user import User
from app.services.github_service import GitHubService


class RepositoryService:
    @staticmethod
    async def get_user_github_token(db: AsyncSession, user_id: int) -> str:
        """Retrieve GitHub token for user."""
        stmt = select(GitHubConnection).where(GitHubConnection.user_id == user_id)
        result = await db.execute(stmt)
        conn = result.scalars().first()
        if not conn or not conn.access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account is not connected. Please connect GitHub first."
            )
        return conn.access_token

    @staticmethod
    async def list_connected_repositories(db: AsyncSession, user_id: int) -> List[Repository]:
        """List all repositories connected to TALOS for the user."""
        stmt = select(Repository).where(Repository.user_id == user_id).order_by(Repository.updated_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_repository_by_id(db: AsyncSession, user_id: int, repository_id: int) -> Optional[Repository]:
        """Get repository by ID for user."""
        stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def connect_repository(
        db: AsyncSession, user_id: int, github_repo_id: str, full_name: str
    ) -> Repository:
        """Connect a new GitHub repository to TALOS."""
        # Check if already connected
        stmt = select(Repository).where(Repository.user_id == user_id, Repository.github_repo_id == str(github_repo_id))
        result = await db.execute(stmt)
        existing = result.scalars().first()
        if existing:
            return existing

        token = await RepositoryService.get_user_github_token(db, user_id)
        
        parts = full_name.split("/")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid full_name format. Expected 'owner/repo'.")
        
        owner, name = parts[0], parts[1]

        # Fetch real repo data from GitHub
        gh_data = await GitHubService.fetch_repository_detail(token, owner, name)
        default_branch = gh_data.get("default_branch", "main")
        commit_info = await GitHubService.fetch_latest_commit(token, owner, name, default_branch)

        repo = Repository(
            user_id=user_id,
            github_repo_id=str(gh_data.get("id", github_repo_id)),
            name=gh_data.get("name", name),
            full_name=gh_data.get("full_name", full_name),
            owner=gh_data.get("owner", {}).get("login", owner),
            default_branch=default_branch,
            primary_language=gh_data.get("language"),
            visibility="private" if gh_data.get("private") else "public",
            clone_url=gh_data.get("clone_url", f"https://github.com/{full_name}.git"),
            html_url=gh_data.get("html_url", f"https://github.com/{full_name}"),
            latest_commit_sha=commit_info.get("sha"),
            latest_commit_message=commit_info.get("message"),
            latest_commit_author=commit_info.get("author"),
            latest_commit_date=commit_info.get("date"),
            monitoring_status="active",
            connection_status="connected",
            last_checked_at=datetime.now(timezone.utc)
        )

        db.add(repo)
        await db.commit()
        await db.refresh(repo)
        return repo

    @staticmethod
    async def sync_repository_metadata(
        db: AsyncSession, user_id: int, repository_id: int
    ) -> Repository:
        """Re-sync repository metadata from GitHub."""
        repo = await RepositoryService.get_repository_by_id(db, user_id, repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")

        token = await RepositoryService.get_user_github_token(db, user_id)
        
        try:
            gh_data = await GitHubService.fetch_repository_detail(token, repo.owner, repo.name)
            commit_info = await GitHubService.fetch_latest_commit(token, repo.owner, repo.name, gh_data.get("default_branch", repo.default_branch))

            repo.default_branch = gh_data.get("default_branch", repo.default_branch)
            repo.primary_language = gh_data.get("language", repo.primary_language)
            repo.visibility = "private" if gh_data.get("private") else "public"
            repo.clone_url = gh_data.get("clone_url", repo.clone_url)
            repo.html_url = gh_data.get("html_url", repo.html_url)

            if commit_info.get("sha"):
                repo.latest_commit_sha = commit_info["sha"]
                repo.latest_commit_message = commit_info["message"]
                repo.latest_commit_author = commit_info["author"]
                repo.latest_commit_date = commit_info["date"]

            repo.connection_status = "connected"
            repo.last_checked_at = datetime.now(timezone.utc)
        except Exception as exc:
            repo.connection_status = "error"
            await db.commit()
            raise HTTPException(status_code=400, detail=f"Sync failed: {str(exc)}")

        await db.commit()
        await db.refresh(repo)
        return repo

    @staticmethod
    async def toggle_monitoring_status(
        db: AsyncSession, user_id: int, repository_id: int, status_str: str
    ) -> Repository:
        """Toggle monitoring status between active and paused."""
        repo = await RepositoryService.get_repository_by_id(db, user_id, repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")

        if status_str not in ["active", "paused"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'active' or 'paused'.")

        repo.monitoring_status = status_str
        await db.commit()
        await db.refresh(repo)
        return repo

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession, user_id: int) -> Dict[str, int]:
        """Compute real stats for dashboard from database."""
        stmt_total = select(func.count(Repository.id)).where(Repository.user_id == user_id)
        total_res = await db.execute(stmt_total)
        total = total_res.scalar() or 0

        stmt_active = select(func.count(Repository.id)).where(Repository.user_id == user_id, Repository.monitoring_status == "active")
        active_res = await db.execute(stmt_active)
        active = active_res.scalar() or 0

        # Real count of OPEN issues across user repositories
        stmt_issues = (
            select(func.count(MaintenanceIssue.id))
            .join(Repository, MaintenanceIssue.repository_id == Repository.id)
            .where(Repository.user_id == user_id, MaintenanceIssue.status == "OPEN")
        )
        issues_res = await db.execute(stmt_issues)
        open_issues = issues_res.scalar() or 0

        return {
            "total_repositories": total,
            "active_monitoring_count": active,
            "active_issues_count": open_issues,
            "verified_patches_count": 0,
            "awaiting_review_count": 0,
        }
