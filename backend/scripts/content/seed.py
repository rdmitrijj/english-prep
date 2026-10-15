"""Load content/tests/*.json into the database. Idempotent: run it as often as you like.

    python -m scripts.content.seed

- each section is compared by content hash: unchanged → skipped, new → added, changed → replaced,
  unless someone already answered its questions (then: give the new version a new slug);
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
from app.models.content import AnswerKey, AudioAsset, Part, Passage, Question, QuestionGroup, Section, Tag, Test
from app.models.enums import ContentStatus, TagKind
from app.services.normalize import count_words
from scripts.content.schema import CSection, CTest
from scripts.content.spec import TOPIC_LABELS


async def topic_tag(session: AsyncSession, slug: str) -> Tag:
    tag = await session.scalar(select(Tag).where(Tag.kind == TagKind.topic, Tag.slug == slug))
    if tag is None:
        tag = Tag(kind=TagKind.topic, slug=slug, label=TOPIC_LABELS.get(slug, slug.replace("-", " ").capitalize()))
        session.add(tag)
        await session.flush()
    return tag


async def answered(session: AsyncSession, section_id: int) -> bool:
    return bool(await session.scalar(select(exists().where(
        Response.question_id == Question.id, Question.group_id == QuestionGroup.id,
        QuestionGroup.part_id == Part.id, Part.section_id == section_id))))


async def seed_test(session: AsyncSession, t: CTest) -> str:
    """Upsert one test, section by section: unchanged sections are left alone, new ones are added, changed ones
    are replaced unless someone already answered them (a new Listening section never disturbs an answered Reading)."""
    if t.status != ContentStatus.published:
        return f"skipped ({t.status.value})"
    test = await session.scalar(select(Test).where(Test.slug == t.slug))
    created = test is None
    if created:
        test = Test(slug=t.slug, kind=t.kind, status=t.status, title=t.title, generator_meta={})
        session.add(test)
        await session.flush()
    hashes: dict[str, str] = dict(test.generator_meta.get("section_hashes", {}))
    # ponytail: tests seeded before per-section hashes (M2–M4) adopt the file's hashes for the sections they have.
    legacy = not created and "section_hashes" not in test.generator_meta
    meta = {**t.generator_meta, "section_hashes": hashes}
    outcomes = []
    if not created and (test.kind, test.status, test.title) != (t.kind, t.status, t.title):
        test.kind, test.status, test.title = t.kind, t.status, t.title
        outcomes.append("updated")

    for order, cs in enumerate(t.sections):
        if any(p.script and not p.audio for p in cs.parts):
            outcomes.append(f"{cs.skill}: skipped (audio not rendered yet)")
            continue
        # Without None fields (new optional fields keep old hashes) and without audio: new voices change no question.
        digest = hashlib.sha256(cs.model_dump_json(
            exclude_none=True, exclude={"parts": {"__all__": {"audio"}}}).encode()).hexdigest()
        current = await session.scalar(select(Section).where(Section.test_id == test.id, Section.skill == cs.skill))
        if current and (legacy or hashes.get(cs.skill) == digest):
            hashes[cs.skill] = digest
            if await sync_audio(session, current.id, cs):
                outcomes.append(f"{cs.skill}: audio updated")
            continue
        if current:
            if await answered(session, current.id):
                outcomes.append(f"{cs.skill}: changed but already has answers — give the new version a new slug")
                continue
            await session.execute(delete(Section).where(Section.id == current.id))  # the DB cascades to all children
        await insert_section(session, test.id, order, cs)
        hashes[cs.skill] = digest
        if not created:
            outcomes.append(f"{cs.skill}: {'replaced' if current else 'added'}")
    test.generator_meta = meta
    await session.commit()
    return "created" if created else "; ".join(outcomes) or "unchanged"


def audio_row(part_id: int, audio) -> dict:
    return dict(part_id=part_id, url=audio.url, duration_ms=audio.duration_ms, tts_provider=audio.tts_provider,
                voices=audio.voices, segments=[seg.model_dump() for seg in audio.segments])


async def sync_audio(session: AsyncSession, section_id: int, cs: CSection) -> bool:
    """Re-rendered audio (e.g. real voices replacing test tones) updates in place, even after answers exist."""
    changed = False
    for cp in (p for p in cs.parts if p.audio):
        part = await session.scalar(select(Part).where(Part.section_id == section_id, Part.number == cp.number))
        row = await session.scalar(select(AudioAsset).where(AudioAsset.part_id == part.id))
        new = audio_row(part.id, cp.audio)
        if row is None:
            session.add(AudioAsset(**new))
        elif any(getattr(row, k) != v for k, v in new.items()):
            for k, v in new.items():
                setattr(row, k, v)
        else:
            continue
        changed = True
    return changed


async def insert_section(session: AsyncSession, test_id: int, order: int, cs: CSection) -> None:
    # Explicit foreign keys + flush (to get ids) instead of relationship collections:
    # async sessions can't lazy-load a collection behind the scenes.
    section = Section(test_id=test_id, skill=cs.skill, order=order, duration_s=cs.duration_s)
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
        if cp.audio:
            session.add(AudioAsset(**audio_row(part.id, cp.audio)))
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
