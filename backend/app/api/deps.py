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
    """Dependency to retrieve or auto-create local default user."""
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

    # Fallback to local default user for local dev seamless operation
    stmt = select(User).where(User.username == "talos_developer")
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
