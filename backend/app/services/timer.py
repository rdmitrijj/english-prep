"""Server-authoritative exam clock (PLAN §6.4).

Expiry is lazy: every request that touches an attempt calls `finalize_if_expired` first,
so no background scheduler is needed (the free Render service sleeps when idle anyway).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.attempts import Attempt, AttemptSection
from app.models.enums import SubmitReason
from app.services import scoring

GRACE = timedelta(seconds=10)  # autosaves still accepted this long after the deadline (network delay)


def now() -> datetime:
    """The only clock the app reads; tests replace it to freeze time, DEV_CLOCK_OFFSET_DAYS shifts it in dev."""
    return datetime.now(UTC) + timedelta(days=get_settings().dev_clock_offset_days)


def scaled(duration_s: int) -> int:
    return max(1, round(duration_s * get_settings().exam_time_scale))


def start(asec: AttemptSection, duration_s: int | None, scale: bool = True) -> None:
    """Idempotent: starting twice (double click, refresh) keeps the first deadline.
    `scale=False` for Listening: its time is the recording's length, which EXAM_TIME_SCALE can't shrink."""
    if asec.started_at is None:
        asec.started_at = now()
        seconds = (scaled(duration_s) if scale else duration_s) if duration_s else None
        asec.deadline_at = asec.started_at + timedelta(seconds=seconds) if seconds else None


def accepts_saves(asec: AttemptSection) -> bool:
    return asec.started_at is not None and asec.submitted_at is None and (
        asec.deadline_at is None or now() <= asec.deadline_at + GRACE
    )


async def finalize_if_expired(session: AsyncSession, attempt: Attempt) -> None:
    """Auto-submit every section whose time (plus grace) is up, scoring whatever was saved."""
    for asec in attempt.sections:
        if asec.submitted_at is None and asec.deadline_at and now() > asec.deadline_at + GRACE:
            await scoring.submit_section(session, attempt, asec, SubmitReason.timeout, at=asec.deadline_at)
    await session.commit()
