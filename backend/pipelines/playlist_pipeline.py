"""
Playlist pipeline — fetches all tracks from the user's Spotify playlists
and stores them as UserTrack rows with term="playlist".
"""

import asyncio
from typing import Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.spotify import SpotifyClient
from ..db.models import Track, ReportTrack

Publish = Optional[Callable[[str, str, int], Awaitable[None]]]


async def run_playlist_pipeline(
    report_id: str,
    user_id: str,
    access_token: str,
    db: AsyncSession,
    liked_spotify_ids: set[str],
    publish: Publish = None,
) -> dict:
    """Fetch all playlist tracks and upsert them into the DB."""

    rid = UUID(report_id)
    uid = UUID(user_id)

    async def _pub(step: str, message: str, pct: int) -> None:
        if publish:
            await publish(step, message, pct)

    async with SpotifyClient(access_token) as spotify:
        await _pub("playlists", "Fetching your playlists...", 1)
        playlists = await spotify.get_user_playlists()
        total_playlists = len(playlists)
        await _pub("playlists", f"Found {total_playlists} playlists. Loading tracks...", 3)

        # Collect all tracks from all playlists (deduplicated by spotify_id)
        seen_ids: set[str] = set()
        all_raw_tracks: list[dict] = []

        for i, playlist in enumerate(playlists):
            pid = playlist.get("id")
            pname = playlist.get("name", "")
            if not pid:
                continue
            try:
                items = await spotify.get_playlist_tracks(pid)
                for item in items:
                    raw = item.get("track", {})
                    sid = raw.get("id")
                    if sid and sid not in seen_ids:
                        seen_ids.add(sid)
                        all_raw_tracks.append(raw)
            except Exception:
                pass  # skip unavailable playlists

            pct = 3 + int((i + 1) / total_playlists * 30)
            await _pub("playlists", f"Loaded playlist {i + 1}/{total_playlists}: {pname[:40]}", pct)

    total_tracks = len(all_raw_tracks)
    await _pub("playlists", f"Found {total_tracks} unique tracks across playlists. Saving...", 35)

    # Upsert Track rows and create UserTrack links
    playlist_in_db: list[Track] = []
    for raw_track in all_raw_tracks:
        spotify_id = raw_track.get("id")
        if not spotify_id:
            continue

        images = raw_track.get("album", {}).get("images", [])
        image_url = images[0]["url"] if images else None
        release_date = raw_track.get("album", {}).get("release_date", "")
        release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

        result = await db.execute(select(Track).where(Track.spotify_id == spotify_id))
        track = result.scalar_one_or_none()

        if not track:
            track = Track(
                spotify_id=spotify_id,
                name=raw_track["name"],
                artist=", ".join(a["name"] for a in raw_track.get("artists", [])),
                artist_id=(raw_track["artists"][0]["id"] if raw_track.get("artists") else None),
                album=raw_track.get("album", {}).get("name"),
                release_year=release_year,
                duration_ms=raw_track.get("duration_ms"),
                popularity=raw_track.get("popularity"),
                preview_url=raw_track.get("preview_url"),
                image_url=image_url,
            )
            db.add(track)
            await db.flush()

        db.add(ReportTrack(
            user_id=uid,
            track_id=track.id,
            report_id=rid,
            term="playlist",
            rank=None,
            play_weight=1.0,
        ))
        playlist_in_db.append(track)

    await db.commit()

    liked_count = sum(1 for t in playlist_in_db if t.spotify_id in liked_spotify_ids)
    print(
        f"[playlist_pipeline] Done — {total_tracks} playlist tracks stored, "
        f"{liked_count} are also liked songs"
    )
    await _pub("playlists", f"Saved {total_tracks} playlist tracks ({liked_count} are also liked).", 40)

    return {
        "total_playlists": total_playlists,
        "total_tracks": total_tracks,
        "liked_overlap": liked_count,
    }
