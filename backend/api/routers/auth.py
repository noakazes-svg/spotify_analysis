import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...db.database import get_db
from ...db.models import User

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"

# In-memory OAuth state store: {state: expires_at_unix}
_oauth_states: dict[str, float] = {}
_STATE_TTL = 300  # 5 minutes


def _store_state(state: str) -> None:
    _oauth_states[state] = time.time() + _STATE_TTL
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if v < now]
    for k in expired:
        del _oauth_states[k]


def _consume_state(state: str) -> bool:
    expires_at = _oauth_states.pop(state, None)
    return expires_at is not None and expires_at > time.time()


def _make_jwt(user_id: str, spotify_id: str) -> str:
    payload = {
        "sub": user_id,
        "spotify_id": spotify_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.get("/spotify/login")
async def spotify_login():
    state = secrets.token_urlsafe(16)
    _store_state(state)

    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "state": state,
        "scope": settings.spotify_scopes,
        "show_dialog": "false",
    }
    return RedirectResponse(f"{SPOTIFY_AUTH_URL}?{urlencode(params)}")


@router.get("/spotify/callback")
async def spotify_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        return RedirectResponse(f"{settings.frontend_url}/?error={error}")

    if not state or not _consume_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
            },
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    token_data = token_resp.json()
    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth failed"))

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

    # Fetch user profile
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            SPOTIFY_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    profile = profile_resp.json()

    spotify_id = profile["id"]
    images = profile.get("images") or []
    avatar_url = images[-1]["url"] if images else None

    # Upsert user
    result = await db.execute(select(User).where(User.spotify_id == spotify_id))
    user = result.scalar_one_or_none()

    if user:
        user.display_name = profile.get("display_name")
        user.email = profile.get("email")
        user.avatar_url = avatar_url
        user.country = profile.get("country")
        user.access_token = access_token
        user.refresh_token = refresh_token
        user.token_expires_at = expires_at
        user.last_seen = datetime.now(timezone.utc)
    else:
        user = User(
            spotify_id=spotify_id,
            display_name=profile.get("display_name"),
            email=profile.get("email"),
            avatar_url=avatar_url,
            country=profile.get("country"),
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    jwt_token = _make_jwt(str(user.id), user.spotify_id)

    return RedirectResponse(f"{settings.frontend_url}/connecting?token={jwt_token}")


@router.delete("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}
