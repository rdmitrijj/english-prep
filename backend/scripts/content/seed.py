"""Load content/tests/*.json into the database. Idempotent: run it as often as you like.

    python -m scripts.content.seed

- unchanged files (same content hash) are skipped;
- changed files are replaced, unless someone already answered their questions (then: give it a new slug);
- only `published` tests are loaded.
"""

import asyncio
import hashlib
from pathlib import Path

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionLocal
from app.models.attempts import Response
from app.models.content import AnswerKey, Part, Passage, Question, QuestionGroup, Section, Tag, Test
from app.models.enums import ContentStatus, TagKind
from app.services.normalize import count_words
from scripts.content.schema import CTest
from scripts.content.spec import READING_TOPICS


async def topic_tag(session: AsyncSession, slug: str) -> Tag:
    tag = await session.scalar(select(Tag).where(Tag.kind == TagKind.topic, Tag.slug == slug))
    if tag is None:
        tag = Tag(kind=TagKind.topic, slug=slug, label=READING_TOPICS.get(slug, slug.replace("-", " ").capitalize()))
        session.add(tag)
        await session.flush()
    return tag


async def seed_test(session: AsyncSession, t: CTest) -> str:
    if t.status != ContentStatus.published:
        return f"skipped ({t.status.value})"
    content_hash = hashlib.sha256(t.model_dump_json().encode()).hexdigest()
    existing = await session.scalar(select(Test).where(Test.slug == t.slug))
    outcome = "created"
    if existing:
        if existing.generator_meta.get("content_hash") == content_hash:
            return "unchanged"
        answered = await session.scalar(select(exists().where(
            Response.question_id == Question.id, Question.group_id == QuestionGroup.id,
            QuestionGroup.part_id == Part.id, Part.section_id == Section.id, Section.test_id == existing.id)))
        if answered:
            return "skipped: changed but already has answers — give the new version a new slug"
        await session.execute(delete(Test).where(Test.id == existing.id))  # DB cascades to all children
        outcome = "replaced"

    test = Test(slug=t.slug, kind=t.kind, status=t.status, title=t.title,
                generator_meta={**t.generator_meta, "content_hash": content_hash})
    # Explicit foreign keys + flush (to get ids) instead of relationship collections:
    # async sessions can't lazy-load a collection behind the scenes.
    session.add(test)
    await session.flush()
    for order, cs in enumerate(t.sections):
        section = Section(test_id=test.id, skill=cs.skill, order=order, duration_s=cs.duration_s)
        session.add(section)
        await session.flush()
        for cp in cs.parts:
            tag = await topic_tag(session, cp.topic)
            part = Part(section_id=section.id, number=cp.number, context=cp.context, topic_tag_id=tag.id)
            session.add(part)
            await session.flush()
            if cp.passage:
                session.add(Passage(
                    part_id=part.id, title=cp.passage.title,
                    paragraphs=[p.model_dump() for p in cp.passage.paragraphs],
                    word_count=sum(count_words(p.text) for p in cp.passage.paragraphs),
                    glossary={g.term: g.definition for g in cp.passage.glossary},
                ))
            for g_order, cg in enumerate(cp.groups):
                group = QuestionGroup(
                    part_id=part.id, order=g_order, qtype=cg.qtype, instructions=cg.instructions,
                    max_words=cg.max_words, allow_number=cg.allow_number,
                    options=[o.model_dump() for o in cg.options] if cg.options else None,
                    layout=cg.layout.model_dump() if cg.layout else None,
                )
                session.add(group)
                await session.flush()
                for cq in cg.questions:
                    q = Question(
                        group_id=group.id, number=cq.number, prompt=cq.prompt, difficulty=cq.difficulty,
                        sub_skill=cq.sub_skill, explanation=cq.explanation.model_dump(),
                        evidence=cq.evidence.model_dump(),
                        options=[o.model_dump() for o in cq.options] if cq.options else None,
                    )
                    session.add(q)
                    await session.flush()
                    session.add(AnswerKey(question_id=q.id, accepted=cq.answer, pick=cg.pick))
    await session.commit()
    return outcome


async def seed_all(content_dir: Path) -> dict[str, str]:
    results = {}
    for path in sorted((content_dir / "tests").glob("*.json")):
        t = CTest.model_validate_json(path.read_text())
        async with SessionLocal() as session:
            results[t.slug] = await seed_test(session, t)
    return results


def main() -> None:
    for slug, outcome in asyncio.run(seed_all(Path(get_settings().content_dir))).items():
        print(f"{slug}: {outcome}")


if __name__ == "__main__":
    main()
