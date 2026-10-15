from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attempts import Attempt, Response
from app.models.content import AnswerKey, Part, Passage, Question, QuestionGroup, Section


async def get_attempt(session: AsyncSession, attempt_id: int, user_id: int) -> Attempt | None:
    return await session.scalar(
        select(Attempt).options(selectinload(Attempt.sections))
        .where(Attempt.id == attempt_id, Attempt.user_id == user_id)
    )


async def list_attempts(session: AsyncSession, user_id: int) -> list[Attempt]:
    return list(await session.scalars(
        select(Attempt).options(selectinload(Attempt.sections))
        .where(Attempt.user_id == user_id).order_by(Attempt.id.desc())
    ))


async def section_parts(session: AsyncSession, section_id: int) -> list[tuple[Part, Passage | None]]:
    """Parts with their passage, groups and questions — content only, never answer keys."""
    parts = await session.scalars(
        select(Part).where(Part.section_id == section_id).order_by(Part.number)
        .options(selectinload(Part.question_groups).selectinload(QuestionGroup.questions))
    )
    parts = list(parts)
    passages = {p.part_id: p for p in await session.scalars(select(Passage).where(Passage.part_id.in_([p.id for p in parts])))}
    return [(p, passages.get(p.id)) for p in parts]


async def section_items(session: AsyncSession, section_id: int) -> list[tuple[Question, QuestionGroup, Part, AnswerKey]]:
    """Every question of a section with its key, in question order. For scoring only."""
    rows = await session.execute(
        select(Question, QuestionGroup, Part, AnswerKey)
        .join(QuestionGroup, Question.group_id == QuestionGroup.id)
        .join(Part, QuestionGroup.part_id == Part.id)
        .join(AnswerKey, AnswerKey.question_id == Question.id)
        .where(Part.section_id == section_id).order_by(Question.number)
    )
    return [tuple(r) for r in rows]


async def section_question_ids(session: AsyncSession, section_id: int) -> set[int]:
    return set(await session.scalars(
        select(Question.id).join(QuestionGroup).join(Part).where(Part.section_id == section_id)
    ))


async def responses_by_question(session: AsyncSession, asec_id: int) -> dict[int, Response]:
    rows = await session.scalars(select(Response).where(Response.attempt_section_id == asec_id))
    return {r.question_id: r for r in rows}


async def get_section(session: AsyncSession, section_id: int) -> Section | None:
    return await session.get(Section, section_id)

