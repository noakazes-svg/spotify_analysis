import httpx
from typing import Optional
from datetime import datetime, timedelta, timezone

from .config import get_settings

settings = get_settings()

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"


class SpotifyClient:
    """Async Spotify API client. Use as an async context manager."""

    def __init__(self, access_token: str):
        self._access_token = access_token
        self._http: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "SpotifyClient":
        self._http = httpx.AsyncClient(
            base_url=SPOTIFY_API_BASE,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *_):
        if self._http:
            await self._http.aclose()

    @property
    def http(self) -> httpx.AsyncClient:
        if not self._http:
            raise RuntimeError("SpotifyClient must be used as an async context manager")
        return self._http

    async def get_me(self) -> dict:
        r = await self.http.get("/me")
        r.raise_for_status()
        return r.json()

    async def get_top_tracks(self, term: str = "medium_term", limit: int = 50) -> dict:
        r = await self.http.get("/me/top/tracks", params={"time_range": term, "limit": limit})
        r.raise_for_status()
        return r.json()

    async def get_top_artists(self, term: str = "medium_term", limit: int = 50) -> dict:
        r = await self.http.get("/me/top/artists", params={"time_range": term, "limit": limit})
        r.raise_for_status()
        return r.json()

    async def get_audio_features(self, track_ids: list[str]) -> list[dict]:
        """Fetch audio features for up to 100 tracks per call."""
        all_features: list[dict] = []
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i : i + 100]
            r = await self.http.get("/audio-features", params={"ids": ",".join(batch)})
            r.raise_for_status()
            all_features.extend(f for f in r.json().get("audio_features", []) if f)
        return all_features

    async def get_recently_played(self, limit: int = 50) -> dict:
        r = await self.http.get("/me/player/recently-played", params={"limit": limit})
        r.raise_for_status()
        return r.json()


async def refresh_spotify_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        return r.json()
