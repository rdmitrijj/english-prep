"""Practice (PLAN §1): untimed sessions built from filtered question groups, with feedback after each group.
Answering, autosave and finishing reuse the /attempts endpoints."""

import random

from fastapi import APIRouter, HTTPException, status

from app.models.attempts import Attempt, AttemptSection
from app.models.enums import AttemptMode, Skill
from app.models.writing import WritingSubmission
from app.repositories import attempts as repo
from app.routers.attempts import Session, attempt_out, feedback, load
from app.schemas.attempts import AttemptOut, CheckIn, FeedbackOut, PracticeCreate, PracticeGroup, WritingOption
from app.security import CurrentUser
from app.services import scoring, timer

router = APIRouter(prefix="/practice", tags=["practice"])

SESSION_QUESTIONS = 10  # ponytail: fixed session size; make it a filter if sessions feel too long or short


def level(avg_difficulty: float) -> str:
    return "easy" if avg_difficulty < 2.5 else "medium" if avg_difficulty < 3.5 else "hard"


async def pool(session, user_id: int, skill: Skill) -> list[PracticeGroup]:
    return [PracticeGroup(group_id=gid, qtype=qtype, topic=slug or "general", topic_label=label or "General",
                          level=level(float(avg)), questions=n, seen=seen)
            for gid, qtype, slug, label, avg, n, seen in await repo.practice_pool(session, user_id, skill)]


@router.get("/options", response_model=list[PracticeGroup])
async def options(user: CurrentUser, session: Session, skill: Skill = Skill.reading):
    """Every question group you can practise, with its type, topic and level; the page counts and filters them."""
    return await pool(session, user.id, skill)


@router.get("/writing", response_model=list[WritingOption])
async def writing_options(user: CurrentUser, session: Session):
    """Every Writing task you can practise; the page filters them and you pick one."""
    return [WritingOption(task_id=t.id, task_number=t.task_number, title=title, kind=kind.slug, kind_label=kind.label,
                          topic=topic.slug, topic_label=topic.label, seen=seen)
            for t, title, kind, topic, seen in await repo.writing_pool(session, user.id)]


async def writing_session(body: PracticeCreate, user_id: int, session) -> Attempt:
    if body.writing_task_id not in {o[0].id for o in await repo.writing_pool(session, user_id)}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Writing task not found")
    asec = AttemptSection(section_id=None, skill=Skill.writing, ui_state={})
    timer.start(asec, None)  # untimed, but time is still measured
    attempt = Attempt(user_id=user_id, mode=AttemptMode.practice, test_id=None, sections=[asec])
    session.add(attempt)
    await session.flush()
    session.add(WritingSubmission(attempt_section_id=asec.id, writing_task_id=body.writing_task_id))
    await session.commit()
    return attempt


@router.post("/sessions", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: PracticeCreate, user: CurrentUser, session: Session):
    if body.skill == Skill.writing:
        return await attempt_out(session, await writing_session(body, user.id, session))
    groups = [g for g in await pool(session, user.id, body.skill)
              if body.qtype in (None, g.qtype) and body.topic in (None, g.topic) and body.level in (None, g.level)]
    if not groups:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No practice questions match these filters")
    random.shuffle(groups)
    groups.sort(key=lambda g: g.seen)  # unseen first; the sort is stable, so each half stays shuffled
    picked, total = [], 0
    for g in groups:
        if total >= SESSION_QUESTIONS:
            break
        picked.append(g.group_id)
        total += g.questions

    asec = AttemptSection(section_id=None, skill=body.skill, ui_state={}, group_ids=picked)
    timer.start(asec, None)  # no deadline, but time is still measured
    attempt = Attempt(user_id=user.id, mode=AttemptMode.practice, test_id=None, sections=[asec])
    session.add(attempt)
    await session.commit()
    return await attempt_out(session, attempt)


@router.post("/sessions/{attempt_id}/check-group", response_model=list[FeedbackOut])
async def check_group(attempt_id: int, body: CheckIn, user: CurrentUser, session: Session):
    """Mark one group and return its feedback. Its answers are locked from then on."""
    attempt = await load(session, attempt_id, user.id)
    asec = attempt.sections[0]
    if attempt.mode != AttemptMode.practice or body.group_id not in (asec.group_ids or []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not in this practice session")
    if asec.submitted_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "This practice session is finished")
    responses = await repo.responses_by_question(session, asec.id)
    group_qids = [q.id for q, g, _, _ in await repo.items(session, asec) if g.id == body.group_id]
    if not any(responses.get(qid) and responses[qid].answer is not None for qid in group_qids):
        raise HTTPException(status.HTTP_409_CONFLICT, "Answer at least one question in this group first")
    await scoring.mark(session, asec, only_group=body.group_id)
    await session.commit()
    return [f for f in await feedback(session, asec) if f.group_id == body.group_id]
