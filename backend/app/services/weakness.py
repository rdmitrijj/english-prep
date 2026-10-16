"""Weakness scores (PLAN §4.4), computed on request from responses and essay results (no stats table).

Reading/Listening, per tag (question type, topic, sub-skill), over the last 90 days:
recent answers weigh more (halving every 14 days), small samples are pulled toward your section accuracy,
slowness adds a capped penalty, and nothing is called a weakness before 8 answers.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempts import Attempt, AttemptSection, Response
from app.models.content import BandTable, Part, Question, QuestionGroup, Tag, WritingTask
from app.models.enums import Skill
from app.models.writing import WritingSubmission
from app.services import scoring, timer, writing

WINDOW = timedelta(days=90)
HALF_LIFE_DAYS = 14
PRIOR = 6  # the section-accuracy prior is worth this many answers
MIN_ANSWERS = 8
TARGET_MS = {Skill.reading: 90_000}  # Listening has no pace target: the recording sets the pace


@dataclass
class Answer:
    correct: bool
    age_days: float
    time_ms: int


def weight(age_days: float) -> float:
    return 0.5 ** (age_days / HALF_LIFE_DAYS)


def weighted_accuracy(answers: list[Answer]) -> float:
    total = sum(weight(a.age_days) for a in answers)
    return sum(weight(a.age_days) * a.correct for a in answers) / total if total else 0.0


def tag_score(answers: list[Answer], mu: float, goal: float, target_ms: int | None) -> dict[str, Any]:
    """Smoothed accuracy p, pace ratio r and weakness W = (goal − p) + pace penalty for one tag."""
    n_eff = sum(weight(a.age_days) for a in answers)
    k_eff = sum(weight(a.age_days) * a.correct for a in answers)
    p = (k_eff + PRIOR * mu) / (n_eff + PRIOR)  # Beta(6μ, 6(1−μ)) prior
    times = [a.time_ms for a in answers if a.time_ms > 0]  # 0 = never opened, says nothing about pace
    pace = median(times) / target_ms if target_ms and times else None
    penalty = min(0.15, 0.3 * max(0.0, pace - 1)) if pace else 0.0
    score = goal - p + penalty
    return {"n": len(answers), "accuracy": p, "raw_accuracy": sum(a.correct for a in answers) / len(answers),
            "median_s": median(times) / 1000 if times else None, "pace": pace, "score": score,
            "weak": len(answers) >= MIN_ANSWERS and score > 0}


def goal_for(rows: list[dict[str, Any]], target_band: float) -> float:
    """Share of the 40 questions needed for the target band, from the active band table."""
    raws = [r["min_raw"] for r in rows if r["band"] >= target_band]
    return (min(raws) if raws else 40) / 40


async def section_stats(session: AsyncSession, user_id: int, target_band: float) -> dict[str, Any]:
    """Every tag's stats per skill, plus the most common error classes."""
    now = timer.now()
    rows = await session.execute(
        select(AttemptSection.skill, Response.is_correct, Response.time_ms, Response.updated_at, Response.error_class,
               QuestionGroup.qtype, Question.sub_skill, Tag.slug, Tag.label)
        .join(Question, Response.question_id == Question.id)
        .join(QuestionGroup, Question.group_id == QuestionGroup.id)
        .join(Part, QuestionGroup.part_id == Part.id)
        .outerjoin(Tag, Part.topic_tag_id == Tag.id)
        .join(AttemptSection, Response.attempt_section_id == AttemptSection.id)
        .join(Attempt, AttemptSection.attempt_id == Attempt.id)
        .where(Attempt.user_id == user_id, Response.is_correct.is_not(None), Response.updated_at >= now - WINDOW))
    by_skill: dict[Skill, list] = defaultdict(list)
    for row in rows:
        by_skill[row.skill].append(row)

    out = {}
    for skill, answers_rows in by_skill.items():
        table = await session.scalar(select(BandTable).where(
            BandTable.skill == scoring.BAND_TABLE_SKILL[skill], BandTable.is_active))
        goal = goal_for(table.rows, target_band)
        answers = [Answer(bool(r.is_correct), max(0.0, (now - r.updated_at).total_seconds() / 86400), r.time_ms)
                   for r in answers_rows]
        mu = weighted_accuracy(answers)
        groups: dict[tuple[str, str, str], list[Answer]] = defaultdict(list)
        for r, a in zip(answers_rows, answers):
            groups[("qtype", r.qtype.value, r.qtype.value)].append(a)
            groups[("topic", r.slug or "general", r.label or "General")].append(a)
            if r.sub_skill:
                groups[("sub_skill", r.sub_skill.value, r.sub_skill.value)].append(a)
        errors: dict[str, int] = defaultdict(int)
        for r in answers_rows:
            if r.error_class:
                errors[r.error_class] += 1
        out[skill.value] = {
            "accuracy": mu, "answers": len(answers), "goal": goal, "target_s": (TARGET_MS.get(skill) or 0) / 1000 or None,
            "tags": sorted(({"skill": skill.value, "kind": kind, "key": key, "label": label,
                             **tag_score(a, mu, goal, TARGET_MS.get(skill))}
                            for (kind, key, label), a in groups.items()), key=lambda t: -t["score"]),
            "errors": sorted(({"error_class": e, "count": n} for e, n in errors.items()), key=lambda e: -e["count"])[:8],
        }
    return out


async def writing_stats(session: AsyncSession, user_id: int, target_band: float) -> dict[str, Any]:
    """Recency-weighted criterion averages and recurring error categories from scored essays."""
    now = timer.now()
    rows = await session.execute(
        select(WritingSubmission, WritingTask.task_number)
        .join(WritingTask, WritingSubmission.writing_task_id == WritingTask.id)
        .join(AttemptSection, WritingSubmission.attempt_section_id == AttemptSection.id)
        .join(Attempt, AttemptSection.attempt_id == Attempt.id)
        .where(Attempt.user_id == user_id, WritingSubmission.submitted_at >= now - WINDOW))
    rows = [tuple(r) for r in rows]
    evs = await writing.evaluations(session, [s.id for s, _ in rows])
    crit: dict[str, list[tuple[float, int]]] = defaultdict(list)  # criterion → (weight, band)
    err_w: dict[str, float] = defaultdict(float)
    err_n: dict[str, int] = defaultdict(int)
    err_subs: dict[str, set[int]] = defaultdict(set)
    words_w = 0.0
    for sub, task_number in rows:
        result = writing.result(evs[sub.id])
        if not result or evs[sub.id][0].model == writing.RULE:  # rule bands (empty, ≤20 words) say nothing about skill
            continue
        w = weight((now - sub.submitted_at).total_seconds() / 86400)
        words_w += w * max(sub.word_count, 1)
        for c, v in result["criteria"].items():
            key = ("task_achievement" if task_number == 1 else "task_response") if c == "task" else c
            crit[key].append((w, v["band"]))
        for e in result["errors"]:
            err_w[e["category"]] += w
            err_n[e["category"]] += 1
            err_subs[e["category"]].add(sub.id)
    criteria = [{"key": k, "n": len(v), "average": sum(w * b for w, b in v) / sum(w for w, _ in v)} for k, v in crit.items()]
    for c in criteria:
        c["weak"] = c["average"] < target_band
    errors = sorted(({"category": k, "count": err_n[k], "essays": len(err_subs[k]), "per_100_words": 100 * err_w[k] / words_w,
                      "weak": err_n[k] >= 3 and len(err_subs[k]) >= 2} for k in err_n), key=lambda e: -e["per_100_words"])
    return {"criteria": sorted(criteria, key=lambda c: c["average"]), "errors": errors}
