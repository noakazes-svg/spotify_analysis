from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt as pyjwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.spotify import refresh_spotify_token
from ..db.database import get_db
from ..db.models import User

settings = get_settings()


def _extract_token(request: Request, access_token: str | None) -> str | None:
    """Accept token from httpOnly cookie OR Authorization: Bearer header."""
    if access_token:
        return access_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def get_current_user(
    request: Request,
    access_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_token(request, access_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = pyjwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Proactively refresh Spotify token if expiring within 5 minutes
    now = datetime.now(timezone.utc)
    expires_at = user.token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if (expires_at - now).total_seconds() < 300:
        try:
            token_data = await refresh_spotify_token(user.refresh_token)
            user.access_token = token_data["access_token"]
            user.token_expires_at = now + timedelta(seconds=token_data["expires_in"])
            if "refresh_token" in token_data:
                user.refresh_token = token_data["refresh_token"]
            await db.commit()
            await db.refresh(user)
        except Exception:
            pass

    return user
