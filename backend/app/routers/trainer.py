"""Weakness trainer (PLAN §4.5): ~20 questions mixing due reviews, your weakest tags and your slowest question type.
Sessions are practice sessions (mode `trainer`): checking groups, autosave and finishing reuse those endpoints."""

import random
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.models.attempts import ReviewItem
from app.models.content import Question
from app.models.enums import AttemptMode, Skill
from app.routers.attempts import Session, attempt_out
from app.routers.practice import new_session, pool
from app.schemas.attempts import AttemptOut, PracticeGroup
from app.security import CurrentUser
from app.services import timer, weakness

router = APIRouter(prefix="/trainer", tags=["trainer"])

SIZE = 20
SHARES = {"due": 0.4, "weak": 0.4, "slow": 0.2}


class TrainerCreate(BaseModel):
    skill: Literal[Skill.reading, Skill.listening]
    kind: Literal["qtype", "topic", "sub_skill"] | None = None  # "Train this": one tag instead of your top 3
    key: str | None = None


Candidate = tuple[int, int]  # (group id, questions in it)


def compose(due: list[Candidate], weak: list[Candidate], slow: list[Candidate], fill: list[Candidate],
            size: int = SIZE) -> list[int]:
    """Take whole groups: ~40% due reviews, ~40% weak tags, ~20% slowest type, then top up when a share ran short."""
    picked: list[int] = []
    total = 0

    def take(candidates: list[Candidate], quota: float) -> None:
        nonlocal total
        got = 0
        for gid, n in candidates:
            if got >= quota or total >= size:
                return
            if gid not in picked:
                picked.append(gid)
                got += n
                total += n

    take(due, SHARES["due"] * size)
    take(weak, SHARES["weak"] * size)
    take(slow, SHARES["slow"] * size)
    take(weak + fill, size - total)
    return picked


def fresh_first(groups: list[PracticeGroup]) -> list[Candidate]:
    groups = random.sample(groups, len(groups))
    return [(g.group_id, g.questions) for g in sorted(groups, key=lambda g: g.seen)]  # stable: unseen first, shuffled


@router.post("/sessions", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: TrainerCreate, user: CurrentUser, session: Session):
    groups = await pool(session, user.id, body.skill)
    if not groups:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No questions to train on yet")
    by_id = {g.group_id: g for g in groups}
    due_ids = list(dict.fromkeys(await session.scalars(
        select(Question.group_id).join(ReviewItem, ReviewItem.question_id == Question.id)
        .where(ReviewItem.user_id == user.id, ReviewItem.due_at <= timer.now()).order_by(ReviewItem.due_at))))
    due = [(gid, by_id[gid].questions) for gid in due_ids if gid in by_id]

    stats = (await weakness.section_stats(session, user.id, user.target_band)).get(body.skill.value, {"tags": []})
    tags = [(body.kind, body.key)] if body.kind and body.key else [(t["kind"], t["key"]) for t in stats["tags"] if t["weak"]][:3]
    sub_skills = await group_sub_skills(session, list(by_id))

    def matches(g: PracticeGroup, kind: str, key: str) -> bool:
        return {"qtype": g.qtype.value, "topic": g.topic}.get(kind) == key or (kind == "sub_skill" and key in sub_skills[g.group_id])

    weak = fresh_first([g for g in groups if any(matches(g, k, v) for k, v in tags)])
    paced = [t for t in stats["tags"] if t["kind"] == "qtype" and t["pace"]]
    slowest = max(paced, key=lambda t: t["pace"])["key"] if paced else None
    slow = fresh_first([g for g in groups if g.qtype.value == slowest])
    picked = compose(due, weak, slow, fresh_first(groups))
    return await attempt_out(session, await new_session(session, user.id, AttemptMode.trainer, body.skill, picked))


async def group_sub_skills(session, group_ids: list[int]) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {gid: set() for gid in group_ids}
    for gid, sub in await session.execute(select(Question.group_id, Question.sub_skill).where(Question.group_id.in_(group_ids))):
        if sub:
            out[gid].add(sub.value)
    return out
