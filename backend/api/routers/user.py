import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.progress import progress
from ...db.database import get_db
from ...db.models import Report, User
from ...workers.tasks import run_pipeline
from ..deps import get_current_user

settings = get_settings()
router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "spotify_id": current_user.spotify_id,
        "display_name": current_user.display_name,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "country": current_user.country,
    }


@router.get("/me/report")
async def get_latest_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Prefer the most recent completed report; fall back to most recent of any status
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id, Report.status == "done")
        .order_by(Report.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        result = await db.execute(
            select(Report)
            .where(Report.user_id == current_user.id)
            .order_by(Report.generated_at.desc())
            .limit(1)
        )
        report = result.scalar_one_or_none()
    if not report:
        return None
    return {
        "id": str(report.id),
        "status": report.status,
        "generated_at": report.generated_at.isoformat(),
        "listening_dna": report.listening_dna,
        "archetype_id": report.archetype_id,
        "personality_scores": report.personality_scores,
    }


@router.post("/me/report/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = Report(user_id=current_user.id, status="queued")
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Run pipeline as a FastAPI background task (no Celery/Redis needed)
    background_tasks.add_task(
        run_pipeline,
        str(report.id),
        str(current_user.id),
    )

    return {"report_id": str(report.id), "status": "queued"}


@router.websocket("/me/report/{report_id}/progress")
async def report_progress_ws(websocket: WebSocket, report_id: str):
    """
    Streams pipeline progress to the browser via WebSocket.
    Uses an in-memory queue (no Redis required).
    """
    await websocket.accept()
    queue = progress.subscribe(report_id)

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                break

            await websocket.send_json(event)
            if event.get("step") == "complete":
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        progress.unsubscribe(report_id, queue)
