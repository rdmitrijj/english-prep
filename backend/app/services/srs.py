"""Leitner spaced repetition (PLAN §4.5): a wrong answer anywhere puts the question in box 1, due tomorrow;
a correct answer once it is due moves it up a box; a correct answer in box 5 retires it."""

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempts import ReviewItem

INTERVALS = (1, 3, 7, 16, 35)  # days until the next review, for boxes 1–5


def next_state(box: int | None, due_at: datetime | None, correct: bool, now: datetime) -> tuple[int, datetime] | None:
    """The question's new (box, due date), or None when it is not (or no longer) queued. `box` None = not queued."""
    if not correct:
        return 1, now + timedelta(days=INTERVALS[0])
    if box is None:
        return None
    if due_at > now:  # answered again before it was due: an early repeat proves little, so nothing moves
        return box, due_at
    if box == len(INTERVALS):
        return None  # retired
    return box + 1, now + timedelta(days=INTERVALS[box])


async def record(session: AsyncSession, user_id: int, results: list[tuple[int, bool]], now: datetime) -> None:
    """Apply freshly marked answers (question id, correct) to the user's review queue."""
    if not results:
        return
    items = {r.question_id: r for r in await session.scalars(select(ReviewItem).where(
        ReviewItem.user_id == user_id, ReviewItem.question_id.in_([qid for qid, _ in results])))}
    for qid, correct in results:
        item = items.get(qid)
        new = next_state(item and item.box, item and item.due_at, correct, now)
        if new is None and item:
            await session.execute(delete(ReviewItem).where(ReviewItem.user_id == user_id, ReviewItem.question_id == qid))
            del items[qid]
        elif new and item:
            item.box, item.due_at, item.last_result = *new, correct
        elif new:
            items[qid] = ReviewItem(user_id=user_id, question_id=qid, box=new[0], due_at=new[1], last_result=correct)
            session.add(items[qid])
