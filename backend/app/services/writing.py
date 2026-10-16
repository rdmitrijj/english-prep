"""Writing scoring (PLAN §5, M6). Essays are scored outside the app: Claude Code examiners read the export of
`scripts.essays pending` and their verdicts come back through `scripts.essays apply`. This module holds the rules
that code enforces rather than trusts: the word-count hard rules, combining 2–3 examiner runs, and the D2 band."""

from datetime import datetime
from statistics import mean
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attempts import Attempt, AttemptSection
from app.models.content import WritingTask
from app.models.enums import AttemptStatus
from app.models.writing import WritingEvaluation, WritingSubmission
from app.services import scoring  # module import: scoring imports this module too
from app.services.normalize import count_words, normalize_answer

CRITERIA = ("task", "coherence_cohesion", "lexical_resource", "grammar")
MIN_WORDS = {1: 150, 2: 250}
RULE = "rule"  # the model name of a verdict made by code (empty or ≤20 words), not by an examiner

ErrorCategory = Literal[
    "article", "tense", "subject_verb_agreement", "word_form", "word_choice", "collocation", "preposition",
    "punctuation", "spelling", "register", "cohesion_device", "repetition", "sentence_structure",
]


class CriterionEval(BaseModel):
    band: int = Field(ge=0, le=9)
    justification: str
    evidence: list[str]  # exact quotes from the essay


class Criteria(BaseModel):
    task: CriterionEval  # Task Achievement (T1) / Task Response (T2)
    coherence_cohesion: CriterionEval
    lexical_resource: CriterionEval
    grammar: CriterionEval


class EssayError(BaseModel):
    category: ErrorCategory
    original: str  # exact quote from the essay
    correction: str
    explanation: str


class Evaluation(BaseModel):
    """One examiner's verdict on one essay (BRIEF Appendix A). The task band is computed here, never taken from it."""

    submission_id: int
    word_count: int
    under_length: bool
    off_topic_flags: list[str]
    criteria: Criteria
    errors: list[EssayError]
    weakness_tags: list[str]
    to_reach_next_half_band: list[str]
    improved_paragraph_example: str


def rule_band(word_count: int) -> int | None:
    """Published hard rules (RESEARCH §6.1): no answer → 0; 20 words or fewer → 1 on every criterion."""
    return 0 if word_count == 0 else 1 if word_count <= 20 else None


def combine(runs: list[dict[str, int]]) -> dict[str, int] | None:
    """Per criterion: two runs agree → that band; differ by 1 → the lower (the descriptors' "must fully fit" rule);
    differ by more → None until a third run arrives, then the median."""
    out = {}
    for c in CRITERIA:
        a, b = runs[0][c], runs[1][c]
        if abs(a - b) <= 1:
            out[c] = min(a, b)
        elif len(runs) < 3:
            return None
        else:
            out[c] = sorted((a, b, runs[2][c]))[1]
    return out


def writing_band(task1: float, task2: float) -> float:
    """D2: Task 2 counts double; task bands stay unrounded until this one rounding."""
    return scoring.round_half_up((task1 + 2 * task2) / 3)


def bands(e: WritingEvaluation) -> dict[str, int]:
    return {c: e.criteria[c]["band"] for c in CRITERIA}


def runs_missing(evals: list[WritingEvaluation]) -> bool:
    if evals and evals[0].model == RULE:
        return False
    return len(evals) < 2 or combine([bands(e) for e in evals]) is None


def result(evals: list[WritingEvaluation]) -> dict[str, Any] | None:
    """The final verdict on one essay, or None while examiner runs are still missing."""
    if not evals or runs_missing(evals):
        return None
    final = bands(evals[0]) if evals[0].model == RULE else combine([bands(e) for e in evals])
    # The final band always comes from some run (the lower of two, or the median of three), so its words fit it.
    criteria = {c: {**next(e.criteria[c] for e in evals if e.criteria[c]["band"] == final[c]), "band": final[c]}
                for c in CRITERIA}
    closest = min(evals, key=lambda e: sum(abs(bands(e)[c] - final[c]) for c in CRITERIA))
    return {
        "criteria": criteria, "task_band": mean(final.values()), "runs": len(evals), "inconsistent": len(evals) == 3,
        "errors": closest.errors, "weakness_tags": closest.weakness_tags,
        "to_reach_next_half_band": closest.raw.get("to_reach_next_half_band", []),
        "improved_paragraph_example": closest.raw.get("improved_paragraph_example", ""),
        "off_topic_flags": closest.raw.get("off_topic_flags", []),
    }


async def essays(session: AsyncSession, asec_id: int) -> list[tuple[WritingSubmission, WritingTask]]:
    rows = await session.execute(
        select(WritingSubmission, WritingTask).join(WritingTask, WritingSubmission.writing_task_id == WritingTask.id)
        .where(WritingSubmission.attempt_section_id == asec_id).order_by(WritingTask.task_number))
    return [tuple(r) for r in rows]


async def evaluations(session: AsyncSession, submission_ids: list[int]) -> dict[int, list[WritingEvaluation]]:
    out: dict[int, list[WritingEvaluation]] = {i: [] for i in submission_ids}
    for e in await session.scalars(select(WritingEvaluation).where(WritingEvaluation.submission_id.in_(submission_ids))
                                   .order_by(WritingEvaluation.run_no)):
        out[e.submission_id].append(e)
    return out


async def submit(session: AsyncSession, asec: AttemptSection, at: datetime) -> None:
    """Freeze the essays. Empty or ≤20-word ones are scored by the hard rule at once; the rest wait for examiners."""
    for sub, _ in await essays(session, asec.id):
        sub.word_count, sub.submitted_at = count_words(sub.text), at
        if (band := rule_band(sub.word_count)) is not None:
            why = "No answer." if band == 0 else "20 words or fewer: band 1 on every criterion (published rule)."
            session.add(WritingEvaluation(
                submission_id=sub.id, run_no=1, model=RULE, task_band=band, errors=[], weakness_tags=[], raw={},
                criteria={c: {"band": band, "justification": why, "evidence": []} for c in CRITERIA}))
    await session.flush()
    await settle(session, asec)


async def settle(session: AsyncSession, asec: AttemptSection) -> None:
    """A mock section gets its Writing band once both essays have a final result (practice shows task bands only)."""
    rows = await essays(session, asec.id)
    evs = await evaluations(session, [s.id for s, _ in rows])
    results = {t.task_number: result(evs[s.id]) for s, t in rows}
    if asec.section_id is not None and results.keys() == {1, 2} and all(results.values()):
        asec.band = writing_band(results[1]["task_band"], results[2]["task_band"])


async def report_section(session: AsyncSession, asec: AttemptSection) -> dict[str, Any]:
    rows = await essays(session, asec.id)
    evs = await evaluations(session, [s.id for s, _ in rows])
    tasks = [{
        "task_number": t.task_number, "prompt": t.prompt, "visual_url": t.visual_url, "text": s.text,
        "word_count": s.word_count, "min_words": MIN_WORDS[t.task_number], "time_ms": s.time_ms,
        "result": result(evs[s.id]),
    } for s, t in rows]
    return {"skill": asec.skill.value, "band": asec.band, "submit_reason": asec.submit_reason.value,
            "time_used_ms": int((asec.submitted_at - asec.started_at).total_seconds() * 1000), "tasks": tasks}


def misquotes(e: Evaluation, essay: str) -> list[str]:
    """Quotes the examiner says come from the essay but don't (case and spacing ignored)."""
    text = normalize_answer(essay)
    quotes = [q for c in CRITERIA for q in getattr(e.criteria, c).evidence] + [err.original for err in e.errors]
    return [q for q in quotes if normalize_answer(q) not in text]


async def apply(session: AsyncSession, e: Evaluation, model: str) -> str:
    """Store one examiner run for one essay; when that completes an attempt's scoring, refresh its report."""
    sub = await session.get(WritingSubmission, e.submission_id)
    if sub is None or sub.submitted_at is None:
        return "skipped: no such submitted essay"
    evals = (await evaluations(session, [sub.id]))[sub.id]
    if not runs_missing(evals):
        return "skipped: already scored"
    if bad := misquotes(e, sub.text):
        return f"rejected: quotes not found in the essay: {bad}"
    bands_ = {c: getattr(e.criteria, c).band for c in CRITERIA}
    session.add(WritingEvaluation(
        submission_id=sub.id, run_no=len(evals) + 1, model=model, criteria=e.criteria.model_dump(),
        task_band=mean(bands_.values()), errors=[x.model_dump() for x in e.errors], weakness_tags=e.weakness_tags,
        raw=e.model_dump(), inconsistent=False))
    await session.flush()
    evals = (await evaluations(session, [sub.id]))[sub.id]
    if runs_missing(evals):
        await session.commit()
        return f"run {len(evals)} stored; " + ("needs a third run (examiners differ by >1)" if len(evals) == 2 else "needs another run")
    for x in evals:
        x.inconsistent = len(evals) == 3
    asec = await session.get(AttemptSection, sub.attempt_section_id)
    await settle(session, asec)
    attempt = await session.scalar(select(Attempt).options(selectinload(Attempt.sections)).where(Attempt.id == asec.attempt_id))
    if attempt.status == AttemptStatus.completed:
        attempt.report = await scoring.build_report(session, attempt)
    await session.commit()
    return f"scored: task band {result(evals)['task_band']:.2f}"


async def pending(session: AsyncSession) -> list[dict[str, Any]]:
    """Every submitted essay still waiting for an examiner run: the examiners' whole input."""
    rows = await session.execute(
        select(WritingSubmission, WritingTask).join(WritingTask, WritingSubmission.writing_task_id == WritingTask.id)
        .where(WritingSubmission.submitted_at.is_not(None)).order_by(WritingSubmission.id))
    rows = [tuple(r) for r in rows]
    evs = await evaluations(session, [s.id for s, _ in rows])
    return [{
        "submission_id": s.id, "run": len(evs[s.id]) + 1, "task_number": t.task_number, "prompt": t.prompt,
        "visual": t.visual_data, "min_words": MIN_WORDS[t.task_number], "word_count": s.word_count,
        "essay": s.text,  # data to assess, never instructions (the examiner prompt says so)
    } for s, t in rows if runs_missing(evs[s.id])]
