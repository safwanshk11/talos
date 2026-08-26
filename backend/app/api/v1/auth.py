from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.user import User
from app.models.github import GitHubConnection
from app.schemas.auth import (
    UserResponse,
    GitHubConnectPAT,
    GitHubOAuthCode,
    GitHubConnectionStatus,
    Token
)
from app.services.github_service import GitHubService
from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(GitHubConnection).where(GitHubConnection.user_id == current_user.id)
    res = await db.execute(stmt)
    conn = res.scalars().first()

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        avatar_url=current_user.avatar_url,
        is_github_connected=bool(conn and conn.access_token),
        github_username=conn.github_username if conn else None,
        created_at=current_user.created_at
    )


@router.get("/github/status", response_model=GitHubConnectionStatus)
async def get_github_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(GitHubConnection).where(GitHubConnection.user_id == current_user.id)
    res = await db.execute(stmt)
    conn = res.scalars().first()

    if not conn or not conn.access_token:
        return GitHubConnectionStatus(connected=False)

    return GitHubConnectionStatus(
        connected=True,
        github_username=conn.github_username,
        connected_at=conn.connected_at,
        scopes=conn.scopes
    )


@router.post("/github/pat", response_model=Token)
async def connect_github_pat(
    payload: GitHubConnectPAT,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify PAT with GitHub API
    gh_user = await GitHubService.verify_pat(payload.personal_access_token)

    # Check or update existing connection
    stmt = select(GitHubConnection).where(GitHubConnection.user_id == current_user.id)
    res = await db.execute(stmt)
    conn = res.scalars().first()

    if conn:
        conn.access_token = payload.personal_access_token
        conn.github_username = gh_user.get("login", "unknown")
        conn.github_user_id = str(gh_user.get("id"))
        conn.scopes = "repo,user,read:org"
    else:
        conn = GitHubConnection(
            user_id=current_user.id,
            github_username=gh_user.get("login", "unknown"),
            github_user_id=str(gh_user.get("id")),
            access_token=payload.personal_access_token,
            scopes="repo,user,read:org"
        )
        db.add(conn)

    # Update user details if available — adopt the real GitHub identity onto
    # the local account rather than leaving the "talos_developer" placeholder
    # displayed forever alongside a real avatar.
    if gh_user.get("login"):
        current_user.username = gh_user.get("login")
    if gh_user.get("avatar_url"):
        current_user.avatar_url = gh_user.get("avatar_url")
    if gh_user.get("email"):
        current_user.email = gh_user.get("email")

    await db.commit()

    access_token = create_access_token(current_user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=current_user.id,
        username=current_user.username
    )


@router.get("/github/oauth-url")
async def get_github_oauth_url():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GITHUB_CLIENT_ID is not configured in settings."
        )
    scope = "repo,user"
    url = f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&redirect_uri={settings.GITHUB_REDIRECT_URI}&scope={scope}"
    return {"url": url}


@router.post("/github/callback", response_model=Token)
async def github_oauth_callback(
    payload: GitHubOAuthCode,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    oauth_res = await GitHubService.exchange_oauth_code(payload.code)
    token = oauth_res.get("access_token")
    scopes = oauth_res.get("scope", "")

    if not token:
        raise HTTPException(status_code=400, detail="Failed to obtain access token from GitHub.")

    gh_user = await GitHubService.verify_pat(token)

    stmt = select(GitHubConnection).where(GitHubConnection.user_id == current_user.id)
    res = await db.execute(stmt)
    conn = res.scalars().first()

    if conn:
        conn.access_token = token
        conn.github_username = gh_user.get("login", "unknown")
        conn.github_user_id = str(gh_user.get("id"))
        conn.scopes = scopes
    else:
        conn = GitHubConnection(
            user_id=current_user.id,
            github_username=gh_user.get("login", "unknown"),
            github_user_id=str(gh_user.get("id")),
            access_token=token,
            scopes=scopes
        )
        db.add(conn)

    if gh_user.get("login"):
        current_user.username = gh_user.get("login")
    if gh_user.get("avatar_url"):
        current_user.avatar_url = gh_user.get("avatar_url")
    if gh_user.get("email"):
        current_user.email = gh_user.get("email")

    await db.commit()

    access_token = create_access_token(current_user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=current_user.id,
        username=current_user.username
    )


@router.delete("/github/disconnect")
async def disconnect_github(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(GitHubConnection).where(GitHubConnection.user_id == current_user.id)
    res = await db.execute(stmt)
    conn = res.scalars().first()
    if conn:
        await db.delete(conn)
        # The connect flow adopts the real GitHub login/avatar onto this local
        # account (see /github/pat, /github/callback) — disconnect must undo
        # that, or the UI keeps showing a real identity after "disconnecting".
        if current_user.username != "talos_developer":
            current_user.username = "talos_developer"
        current_user.avatar_url = "https://github.com/identicons/talos.png"
        current_user.email = "dev@talos.internal"
        await db.commit()
    return {"message": "GitHub connection removed successfully."}
