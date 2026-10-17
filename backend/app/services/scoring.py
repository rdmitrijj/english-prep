"""Band arithmetic, section scoring and the attempt report. Conversion tables live in the
`band_tables` DB rows, never in this code."""

import math
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from itertools import groupby
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempts import Attempt, AttemptSection, Response
from app.models.content import AnswerKey, BandTable, Part, Question, QuestionGroup
from app.models.enums import AttemptMode, AttemptStatus, QType, Skill, SubmitReason
from app.repositories import attempts as repo
from app.services import srs, timer, writing  # module imports: timer and writing import this module too
from app.services.normalize import classify_choice, classify_text

BAND_TABLE_SKILL = {Skill.reading: "reading_academic", Skill.listening: "listening"}


def band_for_raw(rows: list[dict[str, Any]], raw: int) -> tuple[float, bool]:
    """Look up a raw score (0–40) in a band table. Returns (band, is_estimate)."""
    for row in rows:
        if row["min_raw"] <= raw <= row["max_raw"]:
            return float(row["band"]), bool(row.get("estimated", False))
    raise ValueError(f"raw score {raw} not covered by band table")


def round_half_up(value: float) -> float:
    """Round to the nearest 0.5, with .25 → up and .75 → up (official IELTS rule, RESEARCH §5)."""
    return math.floor(value * 2 + 0.5) / 2


def overall_band(section_bands: Iterable[float]) -> float:
    bands = list(section_bands)
    return round_half_up(sum(bands) / len(bands))


def is_multi_answer(qtype: QType, group_options: list | None) -> bool:
    """'Choose TWO letters': one checkbox list shared by several question numbers."""
    return qtype == QType.mcq and bool(group_options)


Item = tuple[Question, QuestionGroup, Part, AnswerKey]


def mark_group(group_items: list[Item], responses: dict[int, Response]) -> None:
    """Set is_correct / error_class on every response of one question group."""
    group = group_items[0][1]
    if is_multi_answer(group.qtype, group.options):
        # Every question in the group stores the same selection; each correct letter earns one mark.
        answer = responses[group_items[0][0].id].answer
        chosen = {str(a).upper() for a in answer} if isinstance(answer, list) else set()
        key = {a.upper() for a in group_items[0][3].accepted}
        hits = len(chosen & key) if len(chosen) <= len(group_items) else 0
        for i, (q, _, _, _) in enumerate(group_items):
            r = responses[q.id]
            r.error_class = None if i < hits else ("blank" if not chosen else "wrong_option")
            r.is_correct = r.error_class is None
        return
    for q, g, _, k in group_items:
        r = responses[q.id]
        answer = r.answer if isinstance(r.answer, str) else None
        if g.max_words is not None and not g.options:
            r.error_class = classify_text(answer, k.accepted, g.max_words)
        else:
            r.error_class = classify_choice(answer, k.accepted, g.qtype)
        r.is_correct = r.error_class is None


async def mark(session: AsyncSession, asec: AttemptSection, only_group: int | None = None) -> list[Item]:
    """Mark all questions in scope (or one group). Unanswered ones get a `blank` response row."""
    items = [it for it in await repo.items(session, asec) if only_group is None or it[1].id == only_group]
    responses = await repo.responses_by_question(session, asec.id)
    for q, _, _, _ in items:
        if q.id not in responses:
            responses[q.id] = Response(attempt_section_id=asec.id, question_id=q.id, answer=None,
                                       time_ms=0, change_count=0, flagged=False)
            session.add(responses[q.id])
    unmarked = {q.id for q, _, _, _ in items if responses[q.id].is_correct is None}
    for _, group_items in groupby(items, key=lambda it: it[1].id):
        mark_group(list(group_items), responses)
    # Each answer feeds the review queue once, when first marked (finishing a practice session re-marks checked groups).
    user_id = await session.scalar(select(Attempt.user_id).where(Attempt.id == asec.attempt_id))
    await srs.record(session, user_id, [(qid, bool(responses[qid].is_correct)) for qid in unmarked], timer.now())
    return items


async def score_section(session: AsyncSession, asec: AttemptSection) -> None:
    """Mark everything, then raw → band (mock sections only; practice has no band)."""
    await mark(session, asec)
    responses = await repo.responses_by_question(session, asec.id)
    asec.raw_score = sum(bool(r.is_correct) for r in responses.values())
    if asec.section_id is None:
        return
    table = await session.scalar(select(BandTable).where(
        BandTable.skill == BAND_TABLE_SKILL[asec.skill], BandTable.is_active))
    asec.band, _ = band_for_raw(table.rows, asec.raw_score)
    asec.band_table_id = table.id


async def submit_section(session: AsyncSession, attempt: Attempt, asec: AttemptSection,
                         reason: SubmitReason, at: datetime) -> None:
    if asec.skill == Skill.writing:
        await writing.submit(session, asec, at)  # the band follows once the essays are scored
    else:
        await score_section(session, asec)
    asec.submitted_at, asec.submit_reason = at, reason
    if all(s.submitted_at for s in attempt.sections):
        attempt.status, attempt.finished_at = AttemptStatus.completed, at
        attempt.report = await build_report(session, attempt)


async def build_report(session: AsyncSession, attempt: Attempt) -> dict[str, Any]:
    """A frozen snapshot, so later content edits never change a past report."""
    sections = []
    for asec in attempt.sections:
        if asec.skill == Skill.writing:
            sections.append(await writing.report_section(session, asec))
            continue
        items = await repo.items(session, asec)
        responses = await repo.responses_by_question(session, asec.id)
        table = await session.get(BandTable, asec.band_table_id) if asec.band_table_id else None
        part_no: dict[int, int] = {}  # 1, 2, 3… in order of appearance (practice may mix tests)
        for _, _, p, _ in items:
            part_no.setdefault(p.id, len(part_no) + 1)
        questions = [{
            "number": q.number, "part": part_no[p.id], "qtype": g.qtype.value,
            "answer": responses[q.id].answer, "accepted": k.accepted,
            "is_correct": responses[q.id].is_correct, "error_class": responses[q.id].error_class,
            "time_ms": responses[q.id].time_ms, "flagged": responses[q.id].flagged,
        } for q, g, p, k in items]

        by_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        by_part: dict[int, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0, "time_ms": 0})
        for x in questions:
            by_type[x["qtype"]][0] += x["is_correct"]
            by_type[x["qtype"]][1] += 1
            part = by_part[x["part"]]
            part["correct"] += x["is_correct"]
            part["total"] += 1
            part["time_ms"] += x["time_ms"]

        sections.append({
            "skill": asec.skill.value, "raw": asec.raw_score, "total": len(questions),
            "band": asec.band, "band_is_estimate": bool(table and band_for_raw(table.rows, asec.raw_score)[1]),
            "submit_reason": asec.submit_reason.value,
            "time_used_ms": int((asec.submitted_at - asec.started_at).total_seconds() * 1000),
            "time_on_questions_ms": sum(x["time_ms"] for x in questions),
            "by_type": [{"qtype": t, "correct": c, "total": n} for t, (c, n) in by_type.items()],
            "parts": [{"number": n, **v} for n, v in sorted(by_part.items())],
            "slowest": sorted(({"number": x["number"], "time_ms": x["time_ms"]} for x in questions),
                              key=lambda x: -x["time_ms"])[:5],
            "questions": questions,
        })
    # Rebuilt whenever a Writing band arrives too, so the overall appears with the last section band.
    if attempt.mode == AttemptMode.full_mock:
        bands = [s.band for s in attempt.sections]
        attempt.overall_band = overall_band(bands) if None not in bands else None
        attempt.overall_is_estimate = True  # Speaking is never taken here
    return {"sections": sections}
