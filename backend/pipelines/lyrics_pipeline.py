"""
Lyrics analysis pipeline — fetches lyrics via Genius for top tracks,
computes aggregate word frequency, and stores in the report.
Runs after spotify_ingest; skipped if no Genius token is configured.
"""

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.genius import GeniusClient
from ..db.models import Report, Track, UserTrack

settings = get_settings()

# Limit to top N tracks (by short-term weight) to stay within rate limits
_MAX_TRACKS = 15
_TOP_WORDS = 80


async def run_lyrics_pipeline(
    report_id: str,
    db: AsyncSession,
    publish,
) -> None:
    from uuid import UUID

    rid = UUID(report_id)

    if not settings.genius_access_token:
        return

    genius = GeniusClient(settings.genius_access_token)

    # Load top short-term tracks for this report
    result = await db.execute(
        select(UserTrack, Track)
        .join(Track, UserTrack.track_id == Track.id)
        .where(UserTrack.report_id == rid, UserTrack.term == "short_term")
        .order_by(UserTrack.rank)
        .limit(_MAX_TRACKS)
    )
    rows = result.all()

    if not rows:
        return

    combined: Counter = Counter()
    fetched = 0

    for ut, track in rows:
        try:
            freq = await genius.get_word_frequency(track.name, track.artist.split(",")[0])
            if freq:
                for item in freq:
                    combined[item["word"]] += item["count"]
                fetched += 1
        except Exception:
            continue

    if not combined:
        return

    top_words = [{"word": w, "count": c} for w, c in combined.most_common(_TOP_WORDS)]

    result = await db.execute(select(Report).where(Report.id == rid))
    report = result.scalar_one()
    dna = dict(report.listening_dna or {})
    dna["lyrics_words"] = top_words
    dna["lyrics_tracks_analyzed"] = fetched
    report.listening_dna = dna
    await db.commit()
