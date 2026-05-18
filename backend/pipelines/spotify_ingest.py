"""
Spotify data ingestion pipeline.

Fetches top tracks (3 time ranges), audio features, top artists, and
recently-played history. Stores everything in the database and calls
the publish callback for real-time progress updates.
"""

from collections import Counter
from datetime import datetime
from typing import Awaitable, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.spotify import SpotifyClient
from ..db.models import Report, Track, ReportTrack

TERMS = ["short_term", "medium_term", "long_term"]
TERM_WEIGHT = {"short_term": 3.0, "medium_term": 2.0, "long_term": 1.0}
AUDIO_FEATURE_KEYS = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "speechiness", "liveness", "tempo",
]

Publish = Callable[[str, str, int], Awaitable[None]]


async def run_spotify_ingestion(
    report_id: str,
    user_id: str,
    access_token: str,
    db: AsyncSession,
    publish: Publish,
) -> None:
    from uuid import UUID
    rid = UUID(report_id)
    uid = UUID(user_id)

    async with SpotifyClient(access_token) as spotify:
        # ── 1. Top tracks (3 time ranges) ─────────────────────────────────────
        await publish("tracks", "Fetching your top tracks...", 10)

        all_tracks: dict[str, dict] = {}
        for term in TERMS:
            top = await spotify.get_top_tracks(term=term, limit=50)
            for rank, item in enumerate(top.get("items", []), start=1):
                sid = item["id"]
                if sid not in all_tracks:
                    all_tracks[sid] = {"item": item, "terms": [], "rank_by_term": {}}
                all_tracks[sid]["terms"].append(term)
                all_tracks[sid]["rank_by_term"][term] = rank

        # ── 2. Audio features (deprecated for new apps — skip gracefully) ────────
        await publish("features", "Analyzing audio fingerprints...", 25)

        features_by_id: dict[str, dict] = {}
        track_ids = list(all_tracks.keys())
        if track_ids:
            try:
                features = await spotify.get_audio_features(track_ids)
                features_by_id = {f["id"]: f for f in features if f}
            except Exception:
                pass  # audio-features endpoint deprecated for new apps

        # ── 3. Store tracks + user_track rows ─────────────────────────────────
        await publish("storing", "Mapping your music universe...", 40)

        for spotify_id, data in all_tracks.items():
            item = data["item"]
            images = item.get("album", {}).get("images", [])
            image_url = images[0]["url"] if images else None
            release_date = item.get("album", {}).get("release_date", "")
            release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None
            audio_features = features_by_id.get(spotify_id)

            result = await db.execute(select(Track).where(Track.spotify_id == spotify_id))
            track = result.scalar_one_or_none()

            if not track:
                track = Track(
                    spotify_id=spotify_id,
                    name=item["name"],
                    artist=", ".join(a["name"] for a in item.get("artists", [])),
                    artist_id=(item["artists"][0]["id"] if item.get("artists") else None),
                    album=item.get("album", {}).get("name"),
                    release_year=release_year,
                    duration_ms=item.get("duration_ms"),
                    popularity=item.get("popularity"),
                    preview_url=item.get("preview_url"),
                    image_url=image_url,
                    audio_features=audio_features,
                )
                db.add(track)
                await db.flush()
            elif audio_features and not track.audio_features:
                track.audio_features = audio_features

            for term in data["terms"]:
                db.add(ReportTrack(
                    user_id=uid,
                    track_id=track.id,
                    report_id=rid,
                    term=term,
                    rank=data["rank_by_term"][term],
                    play_weight=TERM_WEIGHT[term],
                ))

        await db.commit()

        # ── 4. Top artists → genre data ────────────────────────────────────────
        await publish("artists", "Discovering your artist profile...", 55)

        all_genres: list[str] = []
        for term in ["medium_term", "long_term"]:
            top_artists = await spotify.get_top_artists(term=term, limit=50)
            for artist in top_artists.get("items", []):
                all_genres.extend(artist.get("genres", []))

        # ── 5. Recently played ─────────────────────────────────────────────────
        await publish("recent", "Reading your recent listening sessions...", 70)

        recent_data = await spotify.get_recently_played(limit=50)
        recent_items = recent_data.get("items", [])

        # ── 6. Compute listening DNA ───────────────────────────────────────────
        await publish("dna", "Computing your listening DNA...", 85)

        dna = _compute_dna(all_tracks, features_by_id, all_genres, recent_items)

        result = await db.execute(select(Report).where(Report.id == rid))
        report = result.scalar_one()
        report.listening_dna = dna
        await db.commit()


def _compute_dna(
    all_tracks: dict,
    features_by_id: dict,
    genres: list[str],
    recent_items: list[dict],
) -> dict:
    # Audio features (may be empty — Spotify deprecated this for new apps)
    buckets: dict[str, list[float]] = {k: [] for k in AUDIO_FEATURE_KEYS}
    for spotify_id, data in all_tracks.items():
        feats = features_by_id.get(spotify_id)
        if not feats:
            continue
        weight = int(sum(TERM_WEIGHT[t] for t in data["terms"]))
        for key in AUDIO_FEATURE_KEYS:
            val = feats.get(key)
            if val is not None:
                buckets[key].extend([val] * weight)
    avg_features = {k: (sum(v) / len(v) if v else 0.0) for k, v in buckets.items()}

    # Genres
    genre_counter = Counter(genres)
    top_genres = [g for g, _ in genre_counter.most_common(15)]
    genre_counts = [{"name": g, "count": c} for g, c in genre_counter.most_common(15)]

    # Time of day
    time_dist = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
    for item in recent_items:
        played_at = item.get("played_at", "")
        if played_at:
            try:
                hour = datetime.fromisoformat(played_at.replace("Z", "+00:00")).hour
                if 6 <= hour < 12:
                    time_dist["morning"] += 1
                elif 12 <= hour < 18:
                    time_dist["afternoon"] += 1
                elif 18 <= hour < 22:
                    time_dist["evening"] += 1
                else:
                    time_dist["night"] += 1
            except ValueError:
                pass

    # Popularity
    pop_vals = [
        data["item"].get("popularity", 60)
        for data in all_tracks.values()
        if data["item"].get("popularity") is not None
    ]
    discovery_rate = sum(1 for p in pop_vals if p < 40) / len(pop_vals) if pop_vals else 0.0
    avg_popularity = sum(pop_vals) / len(pop_vals) if pop_vals else 0.0

    popularity_buckets = [
        {"range": "0–20", "count": sum(1 for p in pop_vals if p <= 20)},
        {"range": "21–40", "count": sum(1 for p in pop_vals if 21 <= p <= 40)},
        {"range": "41–60", "count": sum(1 for p in pop_vals if 41 <= p <= 60)},
        {"range": "61–80", "count": sum(1 for p in pop_vals if 61 <= p <= 80)},
        {"range": "81–100", "count": sum(1 for p in pop_vals if p >= 81)},
    ]

    # Decades
    years = [
        data["item"].get("album", {}).get("release_date", "")[:4]
        for data in all_tracks.values()
    ]
    decade_counter = Counter(f"{int(y) // 10 * 10}s" for y in years if y and y.isdigit())
    dominant_decade = decade_counter.most_common(1)[0][0] if decade_counter else None
    decade_distribution = [
        {"decade": d, "count": c}
        for d, c in sorted(decade_counter.items())
    ]

    # Top artists
    artist_counter: Counter = Counter()
    for data in all_tracks.values():
        for artist in data["item"].get("artists", []):
            name = artist.get("name", "")
            if name:
                artist_counter[name] += 1
    top_artists = [{"name": n, "count": c} for n, c in artist_counter.most_common(10)]

    return {
        "avg_features": avg_features,
        "top_genres": top_genres,
        "genre_counts": genre_counts,
        "genre_count": len(set(genres)),
        "genre_diversity": min(len(set(genres)) / 20.0, 1.0),
        "discovery_rate": discovery_rate,
        "avg_popularity": avg_popularity,
        "popularity_buckets": popularity_buckets,
        "total_unique_tracks": len(all_tracks),
        "time_distribution": time_dist,
        "dominant_decade": dominant_decade,
        "decade_distribution": decade_distribution,
        "top_artists": top_artists,
    }
