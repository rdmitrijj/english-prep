"""Progress dashboard (PLAN §1): band trend, weaknesses with "Train this", accuracy and pace per tag, writing criteria.
Attempt history and drill-down reuse GET /attempts and /attempts/{id}/report."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.models.attempts import Attempt, AttemptSection, ReviewItem
from app.models.enums import AttemptMode
from app.routers.attempts import Session
from app.security import CurrentUser
from app.services import timer, weakness

router = APIRouter(tags=["dashboard"])
TOP = 5


@router.get("/dashboard")
async def dashboard(user: CurrentUser, session: Session) -> dict[str, Any]:
    bands = await session.execute(
        select(AttemptSection.attempt_id, AttemptSection.skill, AttemptSection.band, AttemptSection.submitted_at)
        .join(Attempt, AttemptSection.attempt_id == Attempt.id)
        .where(Attempt.user_id == user.id, Attempt.mode.in_([AttemptMode.section_mock, AttemptMode.full_mock]),
               AttemptSection.band.is_not(None))
        .order_by(AttemptSection.submitted_at))
    due = await session.scalar(select(func.count()).select_from(ReviewItem).where(
        ReviewItem.user_id == user.id, ReviewItem.due_at <= timer.now()))
    skills = await weakness.section_stats(session, user.id, user.target_band)
    weak = sorted((t for s in skills.values() for t in s["tags"] if t["weak"]), key=lambda t: -t["score"])
    return {
        "target_band": user.target_band,
        "bands": [{"attempt_id": a, "skill": s.value, "band": b, "date": d} for a, s, b, d in bands],
        "reviews_due": due,
        "weaknesses": weak[:TOP],
        "skills": skills,
        "writing": await weakness.writing_stats(session, user.id, user.target_band),
    }
