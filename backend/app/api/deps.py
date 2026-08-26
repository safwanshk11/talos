from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt, JWTError

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to retrieve the authenticated user.

    In development, a missing/invalid token falls back to an auto-created
    local default user so the app is immediately usable without a login
    round-trip. In production this fallback is a real vulnerability — every
    endpoint behind this dependency would be reachable with zero credentials
    — so it's disabled there: a missing/invalid token is a hard 401. Found
    and fixed in the Phase 9 final safety audit."""
    user_id: Optional[int] = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            sub = payload.get("sub")
            if sub and sub.isdigit():
                user_id = int(sub)
        except JWTError:
            pass

    if user_id:
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        user = res.scalars().first()
        if user:
            return user

    if settings.ENVIRONMENT.lower() == "production":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    # Fallback to the local default user for local dev seamless operation
    # only. This is a genuinely single-tenant system (see README Known
    # Limitations) — there is meant to be exactly one local account, ever.
    # Look it up by "the account that exists" (lowest id), not by the literal
    # username "talos_developer": connecting GitHub renames that account to
    # the real GitHub login (see /github/pat, /github/callback), so matching
    # on the placeholder name would stop finding it the moment it's renamed
    # and silently fork off a second, disconnected duplicate account instead.
    stmt = select(User).order_by(User.id).limit(1)
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user:
        user = User(
            username="talos_developer",
            email="dev@talos.internal",
            avatar_url="https://github.com/identicons/talos.png"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
