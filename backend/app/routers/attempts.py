from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.attempts import Attempt, AttemptSection, Response
from app.models.content import Section, Test
from app.models.enums import AttemptStatus, ContentStatus, Skill, SubmitReason, TestKind
from app.repositories import attempts as repo
from app.schemas.attempts import (
    AttemptCreate, AttemptOut, AttemptSummary, AudioOut, FeedbackOut, GroupOut, PartOut, PassageOut, QuestionOut, ReportOut, ResponseOut,
    SaveIn, SaveOut, SectionOut, SegmentOut,
)
from app.security import CurrentUser
from app.services import scoring, timer

router = APIRouter(prefix="/attempts", tags=["attempts"])
Session = Annotated[AsyncSession, Depends(get_session)]

# Autosave runs every 5 s; a delta above 5 s + 3 s grace means a bug or a sleeping laptop, so it is capped.
MAX_TIME_DELTA_MS = 8_000


async def load(session: AsyncSession, attempt_id: int, user_id: int) -> Attempt:
    attempt = await repo.get_attempt(session, attempt_id, user_id)
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    await timer.finalize_if_expired(session, attempt)
    return attempt


def find_section(attempt: Attempt, asec_id: int) -> AttemptSection:
    asec = next((s for s in attempt.sections if s.id == asec_id), None)
    if asec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
    return asec


async def feedback(session: AsyncSession, asec: AttemptSection) -> list[FeedbackOut]:
    responses = await repo.responses_by_question(session, asec.id)
    return [FeedbackOut(
        question_id=q.id, group_id=g.id, number=q.number, answer=r.answer, accepted=k.accepted,
        is_correct=r.is_correct, error_class=r.error_class, explanation=q.explanation, evidence=q.evidence,
    ) for q, g, _, k in await repo.items(session, asec) if (r := responses.get(q.id)) and r.is_correct is not None]


async def shown_seconds(session: AsyncSession, section: Section | None) -> int | None:
    seconds = await repo.section_seconds(session, section) if section else None
    return seconds and (seconds if section.skill == Skill.listening else timer.scaled(seconds))


async def attempt_out(session: AsyncSession, attempt: Attempt) -> AttemptOut:
    test = await session.get(Test, attempt.test_id) if attempt.test_id else None
    sections = []
    for asec in attempt.sections:
        section = await session.get(Section, asec.section_id) if asec.section_id else None
        parts = None
        if asec.started_at:
            parts = [PartOut(
                number=part.number if section else i + 1,  # practice: passages numbered within the session
                passage=PassageOut.model_validate(passage) if passage else None,
                audio=AudioOut.model_validate(audio) if audio else None,
                transcript=[SegmentOut.model_validate(seg) for seg in audio.segments] if audio and not section else None,
                groups=[GroupOut(
                    id=g.id, qtype=g.qtype, instructions=g.instructions, max_words=g.max_words,
                    options=g.options, layout=g.layout,
                    pick=len(g.questions) if scoring.is_multi_answer(g.qtype, g.options) else 1,
                    questions=[QuestionOut.model_validate(q) for q in g.questions],
                ) for g in groups],
            ) for i, (part, passage, audio, groups) in enumerate(await repo.parts_with_groups(session, asec))]
        sections.append(SectionOut(
            id=asec.id, skill=asec.skill,
            duration_s=await shown_seconds(session, section),
            started_at=asec.started_at, deadline_at=asec.deadline_at,
            submitted_at=asec.submitted_at, submit_reason=asec.submit_reason, ui_state=asec.ui_state,
            responses=[ResponseOut.model_validate(r) for r in (await repo.responses_by_question(session, asec.id)).values()],
            parts=parts,
            # Keys only ever leave the server for practice groups the user has already checked.
            feedback=await feedback(session, asec) if asec.section_id is None else [],
        ))
    return AttemptOut(id=attempt.id, mode=attempt.mode, status=attempt.status,
                      test_title=test.title if test else "Practice", server_now=timer.now(), sections=sections)


@router.get("", response_model=list[AttemptSummary])
async def list_attempts(user: CurrentUser, session: Session):
    attempts = await repo.list_attempts(session, user.id)
    for a in attempts:
        if a.status == AttemptStatus.in_progress:
            await timer.finalize_if_expired(session, a)
    titles = dict((await session.execute(select(Test.id, Test.title).where(Test.id.in_({a.test_id for a in attempts})))).all())
    return [AttemptSummary(id=a.id, mode=a.mode, status=a.status, test_title=titles.get(a.test_id, "Practice"),
                           skills=[s.skill for s in a.sections], started_at=a.started_at,
                           bands=[s.band for s in a.sections]) for a in attempts]


@router.post("", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
async def create_attempt(body: AttemptCreate, user: CurrentUser, session: Session):
    test = await session.get(Test, body.test_id)
    if test is None or test.kind != TestKind.mock or test.status != ContentStatus.published:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mock test not found")
    section = await session.scalar(select(Section).where(Section.test_id == test.id, Section.skill == body.skill))
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"This test has no {body.skill} section")
    attempt = Attempt(user_id=user.id, mode=body.mode, test_id=test.id,
                      sections=[AttemptSection(section_id=section.id, skill=section.skill, ui_state={})])
    session.add(attempt)
    await session.commit()
    return await attempt_out(session, attempt)


@router.get("/{attempt_id}", response_model=AttemptOut)
async def get_attempt(attempt_id: int, user: CurrentUser, session: Session):
    return await attempt_out(session, await load(session, attempt_id, user.id))


@router.post("/{attempt_id}/sections/{asec_id}/start", response_model=AttemptOut)
async def start_section(attempt_id: int, asec_id: int, user: CurrentUser, session: Session):
    attempt = await load(session, attempt_id, user.id)
    asec = find_section(attempt, asec_id)
    section = await session.get(Section, asec.section_id) if asec.section_id else None
    if section:
        timer.start(asec, await repo.section_seconds(session, section), scale=section.skill != Skill.listening)
    await session.commit()
    return await attempt_out(session, attempt)


@router.put("/{attempt_id}/sections/{asec_id}/responses", response_model=SaveOut)
async def save_responses(attempt_id: int, asec_id: int, body: SaveIn, user: CurrentUser, session: Session):
    """Batch autosave: answers, flags, time deltas and the highlights/notes UI state."""
    attempt = await load(session, attempt_id, user.id)
    asec = find_section(attempt, asec_id)
    if not timer.accepts_saves(asec):
        raise HTTPException(status.HTTP_409_CONFLICT, "This section is closed")
    valid_ids = await repo.question_ids(session, asec)
    existing = await repo.responses_by_question(session, asec.id)
    for item in body.responses:
        if item.question_id not in valid_ids:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Question {item.question_id} is not in this section")
        r = existing.get(item.question_id)
        answer = item.answer or None  # "" and [] mean "no answer"
        # Practice: once a group is checked its answers are locked (time and the review flag still update).
        if r is not None and r.is_correct is not None and answer != r.answer:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Question {item.question_id} was already checked")
        if r is None:
            r = Response(attempt_section_id=asec.id, question_id=item.question_id, answer=None,
                         time_ms=0, change_count=0, flagged=False)
            session.add(r)
            existing[item.question_id] = r
        if answer != r.answer:
            if r.answer is not None:
                r.change_count += 1
            if answer is not None and r.first_answered_at is None:
                r.first_answered_at = timer.now()
            r.answer = answer
        r.flagged = item.flagged
        r.time_ms += min(item.time_ms, MAX_TIME_DELTA_MS)
    if body.ui_state is not None:
        asec.ui_state = body.ui_state
    await session.commit()
    return SaveOut(server_now=timer.now(), deadline_at=asec.deadline_at)


@router.post("/{attempt_id}/sections/{asec_id}/submit", response_model=AttemptOut)
async def submit_section(attempt_id: int, asec_id: int, user: CurrentUser, session: Session):
    attempt = await load(session, attempt_id, user.id)
    asec = find_section(attempt, asec_id)
    if asec.started_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This section has not started")
    if asec.submitted_at is None:
        await scoring.submit_section(session, attempt, asec, SubmitReason.user, at=timer.now())
        await session.commit()
    return await attempt_out(session, attempt)


@router.get("/{attempt_id}/report", response_model=ReportOut)
async def get_report(attempt_id: int, user: CurrentUser, session: Session):
    attempt = await load(session, attempt_id, user.id)
    if attempt.status != AttemptStatus.completed:
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is not finished yet")
    test = await session.get(Test, attempt.test_id) if attempt.test_id else None
    return ReportOut(id=attempt.id, test_title=test.title if test else "Practice", mode=attempt.mode, finished_at=attempt.finished_at,
                     overall_band=attempt.overall_band, report=attempt.report)
