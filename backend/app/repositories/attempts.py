from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attempts import Attempt, AttemptSection, Response
from sqlalchemy.orm import aliased

from app.models.content import (
    AnswerKey, AudioAsset, Part, Passage, Question, QuestionGroup, Section, Tag, Test, WritingTask, writing_task_tags,
)
from app.models.enums import AttemptStatus, ContentStatus, Skill, TestKind
from app.models.writing import WritingSubmission


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


def _in_scope(query: Select, asec: AttemptSection) -> Select:
    """A mock section covers a whole test section; a practice session covers its picked groups."""
    if asec.section_id is not None:
        return query.where(Part.section_id == asec.section_id)
    return query.where(QuestionGroup.id.in_(asec.group_ids or []))


Content = tuple[Part, Passage | None, AudioAsset | None, list[QuestionGroup]]


async def parts_with_groups(session: AsyncSession, asec: AttemptSection) -> list[Content]:
    """Content the candidate sees, part by part — never answer keys."""
    groups = list(await session.scalars(
        _in_scope(select(QuestionGroup).join(Part, QuestionGroup.part_id == Part.id), asec)
        .options(selectinload(QuestionGroup.questions), selectinload(QuestionGroup.part))
        .order_by(QuestionGroup.part_id, QuestionGroup.order)
    ))
    if asec.group_ids:  # keep the session's own order of parts (first picked first)
        rank = {gid: i for i, gid in enumerate(asec.group_ids)}
        first = {}
        for g in groups:
            first[g.part_id] = min(first.get(g.part_id, len(rank)), rank[g.id])
        groups.sort(key=lambda g: (first[g.part_id], g.order))
    part_ids = {g.part_id for g in groups}
    passages = {p.part_id: p for p in await session.scalars(select(Passage).where(Passage.part_id.in_(part_ids)))}
    audios = {a.part_id: a for a in await session.scalars(select(AudioAsset).where(AudioAsset.part_id.in_(part_ids)))}
    out: list[Content] = []
    for g in groups:
        if not out or out[-1][0].id != g.part_id:
            out.append((g.part, passages.get(g.part_id), audios.get(g.part_id), []))
        out[-1][3].append(g)
    return out


LISTENING_REVIEW_S = 120  # the 2-minute review after the recording (RESEARCH §2.1)


async def section_seconds(session: AsyncSession, section: Section) -> int | None:
    """Reading/Writing: the fixed duration. Listening: the recording's length plus the review."""
    if section.skill != Skill.listening:
        return section.duration_s
    total_ms = await session.scalar(
        select(func.sum(AudioAsset.duration_ms)).join(Part, AudioAsset.part_id == Part.id).where(Part.section_id == section.id))
    return -(-(total_ms or 0) // 1000) + LISTENING_REVIEW_S


async def items(session: AsyncSession, asec: AttemptSection) -> list[tuple[Question, QuestionGroup, Part, AnswerKey]]:
    """Every question in scope with its key, grouped by group. For scoring and feedback only."""
    rows = await session.execute(_in_scope(
        select(Question, QuestionGroup, Part, AnswerKey)
        .join(QuestionGroup, Question.group_id == QuestionGroup.id)
        .join(Part, QuestionGroup.part_id == Part.id)
        .join(AnswerKey, AnswerKey.question_id == Question.id), asec)
        .order_by(QuestionGroup.part_id, QuestionGroup.order, Question.number)
    )
    return [tuple(r) for r in rows]


async def question_ids(session: AsyncSession, asec: AttemptSection) -> set[int]:
    return set(await session.scalars(_in_scope(select(Question.id).join(QuestionGroup).join(Part), asec)))


async def responses_by_question(session: AsyncSession, asec_id: int) -> dict[int, Response]:
    rows = await session.scalars(select(Response).where(Response.attempt_section_id == asec_id))
    return {r.question_id: r for r in rows}


def _completed_mocks(user_id: int) -> Select:
    return select(Attempt.test_id).where(
        Attempt.user_id == user_id, Attempt.status == AttemptStatus.completed, Attempt.test_id.is_not(None))


async def writing_pool(session: AsyncSession, user_id: int) -> list:
    """Writing tasks available for practice (same rule as practice_pool): (task, test title, kind tag, topic tag, seen)."""
    kind, topic = aliased(Tag), aliased(Tag)
    seen = (select(WritingSubmission.writing_task_id)
            .join(AttemptSection, WritingSubmission.attempt_section_id == AttemptSection.id)
            .join(Attempt, AttemptSection.attempt_id == Attempt.id)
            .where(Attempt.user_id == user_id, WritingSubmission.submitted_at.is_not(None)))
    rows = await session.execute(
        select(WritingTask, Test.title, kind, topic, WritingTask.id.in_(seen))
        .join(Part, WritingTask.part_id == Part.id).join(Section, Part.section_id == Section.id)
        .join(Test, Section.test_id == Test.id)
        .join(writing_task_tags, writing_task_tags.c.writing_task_id == WritingTask.id)
        .join(kind, kind.id == writing_task_tags.c.tag_id)
        .join(topic, topic.id == Part.topic_tag_id)
        .where(Test.status == ContentStatus.published,
               or_(Test.kind == TestKind.practice, Test.id.in_(_completed_mocks(user_id))))
        .order_by(WritingTask.task_number, WritingTask.id)
    )
    return list(rows)


async def practice_pool(session: AsyncSession, user_id: int, skill: Skill) -> list:
    """Question groups available for practice: all practice tests, plus mocks this user has completed
    (a mock's items join the pool only afterwards, so a mock is never spoiled). One row per group."""
    completed_mocks = _completed_mocks(user_id)
    seen = (select(Question.group_id)
            .join(Response, Response.question_id == Question.id)
            .join(AttemptSection, Response.attempt_section_id == AttemptSection.id)
            .join(Attempt, AttemptSection.attempt_id == Attempt.id)
            .where(Attempt.user_id == user_id, Response.is_correct.is_not(None)))
    rows = await session.execute(
        select(QuestionGroup.id, QuestionGroup.qtype, Tag.slug, Tag.label,
               func.avg(Question.difficulty), func.count(Question.id), QuestionGroup.id.in_(seen))
        .join(Question, Question.group_id == QuestionGroup.id)
        .join(Part, QuestionGroup.part_id == Part.id)
        .join(Section, Part.section_id == Section.id)
        .join(Test, Section.test_id == Test.id)
        .outerjoin(Tag, Part.topic_tag_id == Tag.id)
        .where(Section.skill == skill, Test.status == ContentStatus.published,
               or_(Test.kind == TestKind.practice, Test.id.in_(completed_mocks)))
        .group_by(QuestionGroup.id, Tag.slug, Tag.label)
        .order_by(QuestionGroup.id)
    )
    return list(rows)
