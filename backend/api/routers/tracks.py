from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func as sqlfunc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_db
from ...db.models import Report, Track, User, UserTrack
from ..deps import get_current_user

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/top")
async def get_top_tracks(
    term: str = Query("medium_term", pattern="^(short_term|medium_term|long_term)$"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        return []

    result = await db.execute(
        select(UserTrack, Track)
        .join(Track, UserTrack.track_id == Track.id)
        .where(and_(UserTrack.report_id == report.id, UserTrack.term == term))
        .order_by(UserTrack.rank)
        .limit(limit)
    )

    return [
        {
            "rank": ut.rank,
            "term": ut.term,
            "track": {
                "id": str(track.id),
                "spotify_id": track.spotify_id,
                "name": track.name,
                "artist": track.artist,
                "album": track.album,
                "release_year": track.release_year,
                "popularity": track.popularity,
                "image_url": track.image_url,
                "preview_url": track.preview_url,
                "audio_features": track.audio_features,
            },
        }
        for ut, track in result.all()
    ]


@router.get("/liked")
async def get_liked_tracks(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        return {"total": 0, "tracks": []}

    total_result = await db.execute(
        select(sqlfunc.count())
        .select_from(UserTrack)
        .where(and_(UserTrack.report_id == report.id, UserTrack.term == "liked"))
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(UserTrack, Track)
        .join(Track, UserTrack.track_id == Track.id)
        .where(and_(UserTrack.report_id == report.id, UserTrack.term == "liked"))
        .offset(offset)
        .limit(limit)
    )

    return {
        "total": total,
        "tracks": [
            {
                "track": {
                    "id": str(track.id),
                    "spotify_id": track.spotify_id,
                    "name": track.name,
                    "artist": track.artist,
                    "album": track.album,
                    "release_year": track.release_year,
                    "popularity": track.popularity,
                    "image_url": track.image_url,
                    "preview_url": track.preview_url,
                    "has_lyrics": track.lyrics_raw is not None,
                },
            }
            for ut, track in result.all()
        ],
    }


@router.get("/{track_id}/deep-dive")
async def get_track_deep_dive(
    track_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    result = await db.execute(select(Track).where(Track.id == UUID(track_id)))
    track = result.scalar_one_or_none()
    if not track:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Track not found")

    emotions = None
    if track.emotions:
        emotions = {
            "joy": track.emotions.joy,
            "sadness": track.emotions.sadness,
            "anger": track.emotions.anger,
            "fear": track.emotions.fear,
            "nostalgia": track.emotions.nostalgia,
            "longing": track.emotions.longing,
            "valence": track.emotions.valence,
            "arousal": track.emotions.arousal,
            "dominant": track.emotions.dominant_emotion,
            "theme_tags": track.emotions.theme_tags,
        }

    return {
        "id": str(track.id),
        "name": track.name,
        "artist": track.artist,
        "album": track.album,
        "release_year": track.release_year,
        "popularity": track.popularity,
        "image_url": track.image_url,
        "audio_features": track.audio_features,
        "lyrics_cleaned": track.lyrics_cleaned,
        "emotions": emotions,
    }
