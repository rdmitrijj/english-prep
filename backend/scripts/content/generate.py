"""Generate Reading content (PLAN §6.9). Run inside the backend container:

    python -m scripts.content.generate reading-mock --slug mock-01
    python -m scripts.content.generate reading-practice --types tfng,note_completion [--topic psychology]

Writes content/tests/<slug>.json with status `published` (all checks + blind solve passed) or `needs_review`.
"""

import argparse
import asyncio
import json
import random
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.models.enums import ContentStatus, QType, Skill, TestKind
from app.services import llm
from scripts.content import prompts
from scripts.content.checks import check_passage, check_reading_part, check_test
from scripts.content.schema import CGroup, CPart, CPassage, CQuestion, CSection, CTest, GroupsDraft, Option, PassageDraft
from scripts.content.spec import MOCK_READING, READING_TOPICS, READING_WORDS, GroupSpec, PassageSpec, instructions, letters
from scripts.content.verify import verify_part

MAX_TRIES = 2


def tests_dir() -> Path:
    path = Path(get_settings().content_dir) / "tests"
    path.mkdir(parents=True, exist_ok=True)
    return path


def existing_titles() -> list[str]:
    titles = []
    for f in tests_dir().glob("*.json"):
        t = CTest.model_validate_json(f.read_text())
        titles += [p.passage.title for s in t.sections for p in s.parts if p.passage]
    return titles


async def generate_passage(spec: PassageSpec, avoid: list[str]) -> CPassage:
    s = get_settings()
    min_par = max(5, *(g.count for g in spec.groups if g.qtype == QType.matching_headings), 0)
    system = prompts.PASSAGE_SYSTEM.format(
        min_words=750, max_words=900, target=820, min_par=min_par, max_par=max(8, min_par + 1),
        style=spec.style, style_note=prompts.STYLE_NOTES[spec.style], level=spec.level,
        qtype_needs="; ".join(prompts.QTYPE_NEEDS[g.qtype] for g in spec.groups),
    )
    user = (f"Topic area: {READING_TOPICS[spec.topic]}. Choose a specific, interesting subject within it.\n"
            f"Do NOT write about any of these subjects already used: {avoid or 'none'}.")
    feedback = ""
    for _ in range(MAX_TRIES):
        draft = await llm.structured(purpose="content_generate", model=s.llm_model_generate, system=system,
                                     user=user + feedback, schema=PassageDraft, effort="high")
        errors = check_passage(draft, READING_WORDS, min_par)
        if not errors:
            break
        feedback = f"\n\nYour previous attempt was rejected: {errors}. Fix this."
    return CPassage.model_validate(draft.model_dump())


def group_specs_text(specs: list[GroupSpec], first: int) -> str:
    lines, n = [], first
    for i, g in enumerate(specs, 1):
        extra = []
        if g.max_words:
            extra.append(f"word limit {g.max_words}" + (" (numbers allowed)" if g.allow_number else " (words only, no numbers)"))
        if g.from_list:
            extra.append("from_list: answers chosen from a word list")
        if g.pick > 1:
            extra.append(f"pick = {g.pick}")
        lines.append(f"Group {i}: type={g.qtype.value}, questions {n}–{n + g.count - 1}" + (f", {', '.join(extra)}" if extra else ""))
        n += g.count
    return "\n".join(lines)


def assemble_groups(draft: GroupsDraft, specs: list[GroupSpec], passage: CPassage, passage_no: int, first: int) -> list[CGroup]:
    if len(draft.groups) != len(specs):
        raise ValueError(f"expected {len(specs)} groups, got {len(draft.groups)}")
    groups, n = [], first
    n_par = len(passage.paragraphs)
    for spec, gd in zip(specs, draft.groups):
        options = gd.options
        if spec.qtype == QType.matching_information:  # the paragraph letters ARE the options
            options = [Option(letter=l, text=f"Paragraph {l}") for l in letters(n_par)]
        groups.append(CGroup(
            qtype=spec.qtype,
            instructions=instructions(spec, n, n + spec.count - 1, passage_no, n_par, len(options or [])),
            max_words=spec.max_words, allow_number=spec.allow_number, pick=spec.pick,
            options=options, layout=gd.layout,
            questions=[CQuestion.model_validate(q.model_dump()) for q in gd.questions],
        ))
        n += spec.count
    return groups


async def build_part(spec: PassageSpec, number: int, passage_no: int, first: int, avoid: list[str]) -> CPart:
    s = get_settings()
    passage = await generate_passage(spec, avoid)
    passage_text = "\n".join(f"[{p.label}] {p.text}" for p in passage.paragraphs)
    system = prompts.QUESTIONS_SYSTEM.format(
        type_rules="\n\n".join(prompts.TYPE_RULES[q] for q in dict.fromkeys(g.qtype for g in spec.groups)))
    user = f"PASSAGE (Reading Passage {passage_no}):\n{passage_text}\n\nGROUP SPECS:\n{group_specs_text(spec.groups, first)}"
    feedback, part = "", None
    for _ in range(MAX_TRIES):
        draft = await llm.structured(purpose="content_generate", model=s.llm_model_generate, system=system,
                                     user=user + feedback, schema=GroupsDraft, effort="high")
        try:
            groups = assemble_groups(draft, spec.groups, passage, passage_no, first)
        except ValueError as e:
            feedback = f"\n\nYour previous attempt was rejected: {e}. Fix this."
            continue
        part = CPart(number=number, context="academic_reading", topic=spec.topic, passage=passage, groups=groups)
        errors = check_reading_part(part, READING_WORDS)
        if not errors:
            break
        feedback = "\n\nYour previous attempt was rejected by automatic checks:\n- " + "\n- ".join(errors) + "\nFix all of these."
    if part is None:
        raise llm.LLMError(f"could not assemble question groups for passage {passage_no}")
    await verify_part(part)
    return part


def finalize(test: CTest) -> CTest:
    test.check_errors = check_test(test)
    disputed = any(q.review for q in test.questions())
    test.status = ContentStatus.needs_review if test.check_errors or disputed else ContentStatus.published
    return test


def meta() -> dict:
    s = get_settings()
    return {"prompt_version": prompts.PROMPT_VERSION, "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "models": {"generate": s.llm_model_generate, "verify": s.llm_model_verify}}


async def reading_mock(slug: str) -> CTest:
    specs = MOCK_READING[slug]
    topics = random.Random(slug).sample(sorted(READING_TOPICS), len(specs))
    avoid = existing_titles()
    firsts = [1 + sum(s.count for s in specs[:i]) for i in range(len(specs))]
    for spec, topic in zip(specs, topics):
        spec.topic = spec.topic or topic
    parts = await asyncio.gather(*(build_part(spec, i + 1, i + 1, firsts[i], avoid) for i, spec in enumerate(specs)))
    section = CSection(skill=Skill.reading, duration_s=3600, parts=list(parts))
    path = tests_dir() / f"{slug}.json"
    if path.exists():  # keep other sections (listening/writing come in later milestones)
        test = CTest.model_validate_json(path.read_text())
        test.sections = [s for s in test.sections if s.skill != Skill.reading] + [section]
        test.sections.sort(key=lambda s: list(Skill).index(s.skill))
    else:
        test = CTest(slug=slug, kind=TestKind.mock, title=f"Academic mock test {slug.split('-')[-1]}",
                     status=ContentStatus.needs_review, sections=[section])
    test.generator_meta = meta()
    return finalize(test)


PRACTICE_COUNTS = {QType.tfng: 6, QType.ynng: 5, QType.matching_headings: 5, QType.mcq: 4}


def practice_spec(types: list[QType], topic: str) -> PassageSpec:
    groups = []
    for t in types:
        g = GroupSpec(t, PRACTICE_COUNTS.get(t, 4))
        if t in {QType.sentence_completion, QType.note_completion, QType.table_completion, QType.flowchart_completion,
                 QType.short_answer, QType.summary_completion}:
            g.max_words, g.allow_number = (2, True)
        groups.append(g)
    style = "argumentative" if QType.ynng in types else "discursive"
    return PassageSpec(groups, "medium", style, topic)


async def reading_practice(types: list[QType], topic: str | None) -> CTest:
    topic = topic or random.choice(sorted(READING_TOPICS))
    part = await build_part(practice_spec(types, topic), 1, 1, 1, existing_titles())
    slug = f"practice-reading-{topic}-{datetime.now(UTC):%Y%m%d%H%M%S}"
    test = CTest(slug=slug, kind=TestKind.practice, title=part.passage.title, status=ContentStatus.needs_review,
                 generator_meta=meta(), sections=[CSection(skill=Skill.reading, duration_s=None, parts=[part])])
    return finalize(test)


def save(test: CTest) -> Path:
    path = tests_dir() / f"{test.slug}.json"
    path.write_text(json.dumps(test.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.content.generate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("reading-mock")
    m.add_argument("--slug", required=True, choices=sorted(MOCK_READING))
    p = sub.add_parser("reading-practice")
    p.add_argument("--types", required=True, help=f"comma-separated, from: {', '.join(q.value for q in QType)}")
    p.add_argument("--topic", choices=sorted(READING_TOPICS))
    args = parser.parse_args()

    if args.cmd == "reading-mock":
        test = asyncio.run(reading_mock(args.slug))
    else:
        types = [QType(t.strip()) for t in args.types.split(",")]
        if unsupported := [t.value for t in types if t not in prompts.TYPE_RULES]:
            parser.error(f"not a Reading type generated in M2: {unsupported} (diagram labelling arrives with the renderer in M6)")
        test = asyncio.run(reading_practice(types, args.topic))
    path = save(test)
    flagged = sum(q.review is not None for q in test.questions())
    print(f"{test.status.value}: {path}  ({len(list(test.questions()))} questions, {flagged} disputed, "
          f"{len(test.check_errors)} check errors)")
    for e in test.check_errors:
        print("  check:", e)


if __name__ == "__main__":
    main()
