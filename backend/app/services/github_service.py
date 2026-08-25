from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

GITHUB_API_BASE = "https://api.github.com"


class GitHubService:
    @staticmethod
    async def verify_pat(token: str) -> Dict[str, Any]:
        """Verify Personal Access Token and return GitHub user details."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TALOS-Bot"
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=10.0)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"GitHub token verification failed: {resp.json().get('message', 'Invalid token')}"
                    )
                return resp.json()
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to connect to GitHub API: {str(exc)}"
                )

    @staticmethod
    async def exchange_oauth_code(code: str) -> Dict[str, Any]:
        """Exchange OAuth code for GitHub access token."""
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth Client ID and Secret are not configured in backend settings."
            )

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": settings.GITHUB_CLIENT_ID,
                        "client_secret": settings.GITHUB_CLIENT_SECRET,
                        "code": code,
                        "redirect_uri": settings.GITHUB_REDIRECT_URI,
                    },
                    timeout=10.0
                )
                data = resp.json()
                if "error" in data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"GitHub OAuth error: {data.get('error_description', data['error'])}"
                    )
                return data
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to exchange GitHub OAuth code: {str(exc)}"
                )

    @staticmethod
    async def fetch_user_repositories(token: str) -> List[Dict[str, Any]]:
        """Fetch all repositories accessible by the given token."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TALOS-Bot"
        }
        async with httpx.AsyncClient() as client:
            try:
                # Fetch up to 100 repositories sorted by updated
                resp = await client.get(
                    f"{GITHUB_API_BASE}/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member",
                    headers=headers,
                    timeout=15.0
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch repositories from GitHub: {resp.text}"
                    )
                return resp.json()
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Network error fetching repositories: {str(exc)}"
                )

    @staticmethod
    async def fetch_repository_detail(token: str, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch detailed metadata for a single repository."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TALOS-Bot"
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}", headers=headers, timeout=10.0)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Repository {owner}/{repo} not found on GitHub."
                    )
                return resp.json()
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Error reaching GitHub API: {str(exc)}"
                )

    @staticmethod
    async def fetch_latest_commit(token: str, owner: str, repo: str, branch: str = "main") -> Dict[str, Any]:
        """Fetch latest commit on branch."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TALOS-Bot"
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{branch}",
                    headers=headers,
                    timeout=10.0
                )
                if resp.status_code != 200:
                    # Fallback to getting default branch commits if branch fails
                    resp = await client.get(
                        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
                        headers=headers,
                        timeout=10.0
                    )
                
                if resp.status_code == 200:
                    data = resp.json()
                    commit_obj = data[0] if isinstance(data, list) and len(data) > 0 else data
                    commit_data = commit_obj.get("commit", {})
                    author_data = commit_data.get("author", {})
                    
                    raw_date = author_data.get("date")
                    parsed_date = None
                    if raw_date:
                        try:
                            parsed_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                        except Exception:
                            parsed_date = None

                    return {
                        "sha": commit_obj.get("sha"),
                        "message": commit_data.get("message"),
                        "author": author_data.get("name"),
                        "date": parsed_date
                    }
                return {"sha": None, "message": None, "author": None, "date": None}
            except Exception:
                return {"sha": None, "message": None, "author": None, "date": None}
