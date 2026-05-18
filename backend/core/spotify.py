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

    async def get_artists(self, artist_ids: list[str]) -> list[dict]:
        """Fetch artist data (including genres) for a list of artist IDs, 50 per call."""
        all_artists: list[dict] = []
        for i in range(0, len(artist_ids), 50):
            batch = artist_ids[i:i + 50]
            r = await self.http.get("/artists", params={"ids": ",".join(batch)})
            r.raise_for_status()
            all_artists.extend(a for a in r.json().get("artists", []) if a)
        return all_artists

    async def get_user_playlists(self) -> list[dict]:
        """Fetch all playlists the user owns or follows."""
        items: list[dict] = []
        offset = 0
        while True:
            r = await self.http.get("/me/playlists", params={"limit": 50, "offset": offset})
            r.raise_for_status()
            data = r.json()
            batch = [p for p in data.get("items", []) if p]
            items.extend(batch)
            if not data.get("next") or len(batch) < 50:
                break
            offset += 50
        return items

    async def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Fetch all tracks from a playlist (skips local/unavailable tracks)."""
        items: list[dict] = []
        offset = 0
        while True:
            r = await self.http.get(
                f"/playlists/{playlist_id}/tracks",
                params={
                    "limit": 100,
                    "offset": offset,
                    "fields": "next,items(track(id,name,artists,album(name,release_date,images),duration_ms,popularity,preview_url))",
                },
            )
            r.raise_for_status()
            data = r.json()
            batch = [
                item for item in data.get("items", [])
                if item and item.get("track") and item["track"].get("id")
            ]
            items.extend(batch)
            if not data.get("next") or len(data.get("items", [])) < 100:
                break
            offset += 100
        return items

    async def get_liked_songs(self, page_size: int = 50) -> list[dict]:
        """Fetch all saved/liked tracks, paginating through all pages."""
        items: list[dict] = []
        offset = 0
        while True:
            r = await self.http.get("/me/tracks", params={"limit": page_size, "offset": offset})
            r.raise_for_status()
            data = r.json()
            batch = data.get("items", [])
            items.extend(batch)
            if not data.get("next") or len(batch) < page_size:
                break
            offset += page_size
        return items


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
