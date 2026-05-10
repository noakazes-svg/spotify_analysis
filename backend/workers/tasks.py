"""
Pipeline runner — no Celery or Redis required.
Called by FastAPI BackgroundTasks; runs in the same async event loop.
"""

from ..core.config import get_settings
from ..core.progress import progress

settings = get_settings()


async def run_pipeline(report_id: str, user_id: str) -> None:
    import asyncio
    from datetime import datetime, timezone, timedelta
    from uuid import UUID
    from sqlalchemy import select

    from ..db.database import AsyncSessionLocal
    from ..db.models import Report, User
    from ..pipelines.spotify_ingest import run_spotify_ingestion
    from ..pipelines.lyrics_pipeline import run_lyrics_pipeline
    from ..core.spotify import refresh_spotify_token

    rid = UUID(report_id)
    uid = UUID(user_id)

    async def pub(step: str, message: str, pct: int) -> None:
        await progress.publish(report_id, {"step": step, "message": message, "progress": pct})

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Report).where(Report.id == rid))
            report = result.scalar_one()
            report.status = "processing"
            await db.commit()

            result = await db.execute(select(User).where(User.id == uid))
            user = result.scalar_one()

            # Auto-refresh Spotify token if expired or about to expire
            now = datetime.now(timezone.utc)
            token_expiry = user.token_expires_at
            if token_expiry and token_expiry.tzinfo is None:
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            if not token_expiry or token_expiry <= now + timedelta(minutes=5):
                token_data = await refresh_spotify_token(user.refresh_token)
                user.access_token = token_data["access_token"]
                user.token_expires_at = now + timedelta(seconds=token_data["expires_in"])
                if "refresh_token" in token_data:
                    user.refresh_token = token_data["refresh_token"]
                await db.commit()

            # ── Phase 1: Spotify data ingestion ───────────────────────────────
            await run_spotify_ingestion(
                report_id=report_id,
                user_id=user_id,
                access_token=user.access_token,
                db=db,
                publish=pub,
            )

            # ── Phase 2: Lyrics analysis via Genius ───────────────────────────
            await pub("emotions", "Mapping emotional patterns...", 88)
            await run_lyrics_pipeline(report_id, db, pub)

            # ── Phase 3: Archetype + GPT-4o insights ──────────────────────────
            await pub("archetype", "Uncovering your music archetype...", 93)
            await pub("insights", "Generating AI insights...", 97)

            # Mark done
            result = await db.execute(select(Report).where(Report.id == rid))
            report = result.scalar_one()
            report.status = "done"
            await db.commit()

            await pub("complete", "Your portrait is ready!", 100)

    except Exception as exc:
        await pub("error", f"Analysis failed: {exc}", 0)
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Report).where(Report.id == rid))
            report = result.scalar_one_or_none()
            if report:
                report.status = "failed"
                await db.commit()
        raise

    finally:
        await asyncio.sleep(30)
        progress.cleanup(report_id)
