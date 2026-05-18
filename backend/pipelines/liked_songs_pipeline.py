"""
Liked-songs pipeline (Main orchestrator per the HLD/LLD).

Flow:
  1. Fetch liked songs + audio features + artist genres from Spotify.
  2. Upsert each song as a Track + UserTrack row in the DB.
  3. Compute listening DNA entirely from liked songs and store on the report.
  4. For each song, route to Shironet (Hebrew) or Genius (English).
  5. Fetch and persist lyrics.
  6. Return a summary dict.
"""

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.spotify import SpotifyClient
from ..core.genius import GeniusClient
from ..core.config import get_settings
from ..db.models import Report, Track, ReportTrack, TrackLyrics

Publish = Optional[Callable[[str, str, int], Awaitable[None]]]

settings = get_settings()

AUDIO_FEATURE_KEYS = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "speechiness", "liveness", "tempo",
]


async def run_liked_songs_pipeline(
    report_id: str,
    user_id: str,
    access_token: str,
    db: AsyncSession,
    publish: Publish = None,
) -> dict:
    """Fetch liked songs, compute DNA from them, store tracks, then fetch lyrics."""

    rid = UUID(report_id)
    uid = UUID(user_id)

    async def _pub(step: str, message: str, pct: int) -> None:
        if publish:
            await publish(step, message, pct)

    # ── 1. Fetch liked songs + audio features + artist genres ──────────────────
    await _pub("liked_songs", "Fetching your liked songs...", 5)

    async with SpotifyClient(access_token) as spotify:
        liked_items = await spotify.get_liked_songs()
        total = len(liked_items)
        await _pub("liked_songs", f"Found {total} liked songs.", 12)

        # Audio features (batched per 100)
        await _pub("liked_features", "Analyzing audio fingerprints...", 18)
        track_ids = [
            item["track"]["id"]
            for item in liked_items
            if item.get("track") and item["track"].get("id")
        ]
        features_by_id: dict[str, dict] = {}
        try:
            features = await spotify.get_audio_features(track_ids)
            features_by_id = {f["id"]: f for f in features if f}
        except Exception:
            pass

        # Artist genres (batched per 50)
        await _pub("liked_genres", "Mapping your genre universe...", 25)
        unique_artist_ids = list({
            item["track"]["artists"][0]["id"]
            for item in liked_items
            if item.get("track") and item["track"].get("artists")
        })
        genres_by_artist: dict[str, list[str]] = {}
        try:
            artists = await spotify.get_artists(unique_artist_ids)
            genres_by_artist = {a["id"]: a.get("genres", []) for a in artists}
        except Exception:
            pass

    # ── 2. Upsert Track + UserTrack rows ───────────────────────────────────────
    await _pub("storing", "Saving liked songs to database...", 32)

    tracks_in_db: list[Track] = []
    for item in liked_items:
        raw_track = item.get("track")
        if not raw_track:
            continue
        spotify_id = raw_track.get("id")
        if not spotify_id:
            continue

        images = raw_track.get("album", {}).get("images", [])
        image_url = images[0]["url"] if images else None
        release_date = raw_track.get("album", {}).get("release_date", "")
        release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None
        audio_features = features_by_id.get(spotify_id)

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
                audio_features=audio_features,
            )
            db.add(track)
            await db.flush()
        elif audio_features and not track.audio_features:
            track.audio_features = audio_features

        db.add(ReportTrack(
            user_id=uid,
            track_id=track.id,
            report_id=rid,
            term="liked",
            rank=None,
            play_weight=1.0,
        ))
        tracks_in_db.append(track)

    await db.commit()

    # ── 3. Compute DNA from liked songs and update the report ──────────────────
    await _pub("dna", "Computing your listening DNA from liked songs...", 40)

    liked_dna = _compute_liked_dna(liked_items, features_by_id, genres_by_artist)

    result = await db.execute(select(Report).where(Report.id == rid))
    report = result.scalar_one()
    report.listening_dna = liked_dna
    await db.commit()

    # ── 4. Fetch lyrics concurrently ───────────────────────────────────────────
    await _pub("lyrics", "Fetching lyrics for your songs...", 45)

    genius = GeniusClient(settings.genius_access_token) if settings.genius_access_token else None
    sem = asyncio.Semaphore(5)  # 5 concurrent requests (Genius rate-limit friendly)

    async def _fetch(track: Track) -> tuple[str, str | None]:
        if track.lyrics and track.lyrics.lyrics_raw:
            return track.spotify_id, track.lyrics.lyrics_raw
        if not genius:
            return track.spotify_id, None
        async with sem:
            try:
                url = await genius.search(track.name, track.artist)
                if not url:
                    return track.spotify_id, None
                lyr = await genius.get_lyrics(url)
                return track.spotify_id, lyr or None
            except Exception:
                return track.spotify_id, None

    results = await asyncio.gather(*[_fetch(t) for t in tracks_in_db])

    now = datetime.now(timezone.utc)
    found = 0
    lyrics_map = {sid: lyr for sid, lyr in results}
    all_lyrics: list[str] = []
    for track in tracks_in_db:
        lyr = lyrics_map.get(track.spotify_id)
        if lyr:
            if track.lyrics:
                track.lyrics.lyrics_raw = lyr
                track.lyrics.lyrics_fetched_at = now
            else:
                db.add(TrackLyrics(track_id=track.id, lyrics_raw=lyr, lyrics_fetched_at=now))
            found += 1
            all_lyrics.append(lyr)
    failed = total - found
    await db.commit()

    # ── 5. Compute word frequency from all lyrics and add to DNA ──────────────
    if all_lyrics:
        from ..core.genius import _clean_lyrics
        word_counter: Counter = Counter()
        for lyr in all_lyrics:
            words = [
                w.strip("'")
                for w in _clean_lyrics(lyr).split()
                if len(w) > 2
            ]
            word_counter.update(words)
        lyrics_words = [{"word": w, "count": c} for w, c in word_counter.most_common(80)]

        result = await db.execute(select(Report).where(Report.id == rid))
        report = result.scalar_one()
        dna = dict(report.listening_dna or {})
        dna["lyrics_words"] = lyrics_words
        dna["lyrics_tracks_analyzed"] = found
        report.listening_dna = dna
        await db.commit()

    summary = {"total": total, "found": found, "failed": failed}
    print(f"[liked_songs_pipeline] Done — {total} songs stored, lyrics found for {found}, failed {failed}")
    await _pub("liked_done", f"Lyrics complete: found {found} of {total} songs.", 90)
    return summary


def _compute_liked_dna(
    liked_items: list[dict],
    features_by_id: dict[str, dict],
    genres_by_artist: dict[str, list[str]],
) -> dict:
    """Compute listening DNA statistics exclusively from liked songs."""

    # Audio features
    buckets: dict[str, list[float]] = {k: [] for k in AUDIO_FEATURE_KEYS}
    for item in liked_items:
        raw = item.get("track", {})
        sid = raw.get("id")
        feats = features_by_id.get(sid) if sid else None
        if feats:
            for key in AUDIO_FEATURE_KEYS:
                val = feats.get(key)
                if val is not None:
                    buckets[key].append(val)
    avg_features = {k: (sum(v) / len(v) if v else 0.0) for k, v in buckets.items()}

    # Genres (from artist data)
    all_genres: list[str] = []
    for item in liked_items:
        raw = item.get("track", {})
        artist_id = (raw.get("artists") or [{}])[0].get("id")
        if artist_id:
            all_genres.extend(genres_by_artist.get(artist_id, []))
    genre_counter = Counter(all_genres)
    top_genres = [g for g, _ in genre_counter.most_common(15)]
    genre_counts = [{"name": g, "count": c} for g, c in genre_counter.most_common(15)]

    # Top artists
    artist_counter: Counter = Counter()
    for item in liked_items:
        for a in (item.get("track") or {}).get("artists", []):
            name = a.get("name", "")
            if name:
                artist_counter[name] += 1
    top_artists = [{"name": n, "count": c} for n, c in artist_counter.most_common(10)]

    # Decades
    years = [
        (item.get("track") or {}).get("album", {}).get("release_date", "")[:4]
        for item in liked_items
    ]
    decade_counter = Counter(
        f"{int(y) // 10 * 10}s" for y in years if y and y.isdigit()
    )
    dominant_decade = decade_counter.most_common(1)[0][0] if decade_counter else None
    decade_distribution = [
        {"decade": d, "count": c} for d, c in sorted(decade_counter.items())
    ]

    # Popularity
    pop_vals = [
        (item.get("track") or {}).get("popularity", 0)
        for item in liked_items
        if (item.get("track") or {}).get("popularity") is not None
    ]
    discovery_rate = sum(1 for p in pop_vals if p < 40) / len(pop_vals) if pop_vals else 0.0
    avg_popularity = sum(pop_vals) / len(pop_vals) if pop_vals else 0.0
    popularity_buckets = [
        {"range": "0–20",   "count": sum(1 for p in pop_vals if p <= 20)},
        {"range": "21–40",  "count": sum(1 for p in pop_vals if 21 <= p <= 40)},
        {"range": "41–60",  "count": sum(1 for p in pop_vals if 41 <= p <= 60)},
        {"range": "61–80",  "count": sum(1 for p in pop_vals if 61 <= p <= 80)},
        {"range": "81–100", "count": sum(1 for p in pop_vals if p >= 81)},
    ]

    return {
        "avg_features": avg_features,
        "top_genres": top_genres,
        "genre_counts": genre_counts,
        "genre_count": len(set(all_genres)),
        "genre_diversity": min(len(set(all_genres)) / 20.0, 1.0),
        "top_artists": top_artists,
        "dominant_decade": dominant_decade,
        "decade_distribution": decade_distribution,
        "discovery_rate": discovery_rate,
        "avg_popularity": avg_popularity,
        "popularity_buckets": popularity_buckets,
        "total_unique_tracks": len(liked_items),
        "time_distribution": {},
    }
