"""Speaking scoring (M10). The browser records one answer per examiner question; outside the app, `scripts.speaking
pending` transcribes them with Whisper and exports the interviews, Claude Code examiners score them, and
`scripts.speaking apply` stores the verdicts. Same double-run rule as Writing (writing.combine)."""

from collections.abc import Callable
from datetime import datetime
from statistics import mean
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, undefer

from app.models.attempts import Attempt, AttemptSection
from app.models.content import AudioAsset, Part
from app.models.enums import AttemptStatus, Skill
from app.models.speaking import SpeakingAnswer, SpeakingEvaluation
from app.services import scoring, writing  # module imports: scoring imports this module too
from app.services.normalize import normalize_answer

CRITERIA = ("fluency_coherence", "lexical_resource", "grammar", "pronunciation")
FILLERS = {"um", "uh", "uhm", "er", "erm", "ah", "hmm", "mm"}
LONG_PAUSE_S = 2.0  # a silence this long inside an answer counts as hesitation
UNSURE_P = 0.5  # Whisper word probability below this: possibly unclear pronunciation (a rough signal only)
MAX_AUDIO_BYTES = 4_000_000  # a 2-minute answer is ~0.5 MB of Opus


class Criteria(BaseModel):
    fluency_coherence: writing.CriterionEval
    lexical_resource: writing.CriterionEval
    grammar: writing.CriterionEval
    pronunciation: writing.CriterionEval  # always shown as an estimate: judged from a transcript and ASR confidence


class Evaluation(BaseModel):
    """One examiner's verdict on one interview. The band is computed here, never taken from it."""

    attempt_section_id: int
    off_topic_flags: list[str]
    criteria: Criteria
    errors: list[writing.EssayError]
    weakness_tags: list[str]
    to_reach_next_half_band: list[str]
    improved_paragraph_example: str  # one answer re-spoken about a band higher


# ---------- transcripts ----------

def bare(word: str) -> str:
    return word.strip(" .,!?;:\"'").lower()


def stats(transcripts: list[tuple[dict[str, Any] | None, int]]) -> dict[str, Any]:
    """Fluency numbers over (transcript, duration_ms) pairs: words, words per minute, fillers, long pauses,
    and the words Whisper was unsure of."""
    words = [w for t, _ in transcripts if t for w in t["words"]]
    spoken = [w for w in words if bare(w["w"]) not in FILLERS]
    pauses = sum(b["start"] - a["end"] >= LONG_PAUSE_S for t, _ in transcripts if t for a, b in zip(t["words"], t["words"][1:]))
    minutes = sum(ms for _, ms in transcripts) / 60_000
    return {
        "words": len(spoken),
        "wpm": round(len(spoken) / minutes) if minutes else 0,
        "fillers": len(words) - len(spoken),
        "long_pauses": pauses,
        "unsure_words": [w["w"].strip() for w in spoken if w["p"] < UNSURE_P],
    }


def annotated(transcript: dict[str, Any]) -> str:
    """The transcript with long silences marked, for the examiners: "I think [pause 3.1s] it was…"."""
    out, prev = [], None
    for w in transcript["words"]:
        if prev is not None and w["start"] - prev >= LONG_PAUSE_S:
            out.append(f"[pause {w['start'] - prev:.1f}s]")
        out.append(w["w"].strip())
        prev = w["end"]
    return " ".join(out)


# ---------- answers ----------

async def parts(session: AsyncSession, section_id: int) -> list[tuple[Part, AudioAsset]]:
    rows = await session.execute(select(Part, AudioAsset).join(AudioAsset, AudioAsset.part_id == Part.id)
                                 .where(Part.section_id == section_id).order_by(Part.number))
    return [tuple(r) for r in rows]


async def answers(session: AsyncSession, asec_id: int) -> list[SpeakingAnswer]:
    return list(await session.scalars(select(SpeakingAnswer).where(SpeakingAnswer.attempt_section_id == asec_id)
                                      .order_by(SpeakingAnswer.part_number, SpeakingAnswer.line_no)))


async def save_answer(session: AsyncSession, asec: AttemptSection, part_number: int, line_no: int,
                      audio: bytes, mime: str, duration_ms: int) -> SpeakingAnswer | None:
    """Store (or replace, after a retry) the recording of one answer. None if that line asks no question."""
    audio_row = next((a for p, a in await parts(session, asec.section_id) if p.number == part_number), None)
    segment = audio_row.segments[line_no] if audio_row and 0 <= line_no < len(audio_row.segments) else None
    if not segment or not segment.get("answer_s"):
        return None
    row = await session.scalar(select(SpeakingAnswer).where(
        SpeakingAnswer.attempt_section_id == asec.id, SpeakingAnswer.part_number == part_number, SpeakingAnswer.line_no == line_no))
    if row is None:
        row = SpeakingAnswer(attempt_section_id=asec.id, part_number=part_number, line_no=line_no)
        session.add(row)
    row.question, row.audio, row.mime, row.transcript = segment["text"], audio, mime, None
    row.duration_ms = min(duration_ms, (segment["answer_s"] + 5) * 1000)  # the client's number, capped
    return row


# ---------- scoring ----------

def rule_eval(asec_id: int) -> SpeakingEvaluation:
    why = "No rateable speech was recorded."
    return SpeakingEvaluation(attempt_section_id=asec_id, run_no=1, model=writing.RULE, task_band=0, errors=[],
                              weakness_tags=[], raw={}, criteria={c: {"band": 0, "justification": why, "evidence": []} for c in CRITERIA})


async def evaluations(session: AsyncSession, asec_id: int) -> list[SpeakingEvaluation]:
    return list(await session.scalars(select(SpeakingEvaluation).where(SpeakingEvaluation.attempt_section_id == asec_id)
                                      .order_by(SpeakingEvaluation.run_no)))


async def submit(session: AsyncSession, asec: AttemptSection, at: datetime) -> None:
    """Nothing recorded → band 0 at once; otherwise the band waits for transcription and the examiners."""
    if not await answers(session, asec.id):
        session.add(rule_eval(asec.id))
        await session.flush()
    await settle(session, asec)


async def settle(session: AsyncSession, asec: AttemptSection) -> None:
    if res := writing.result(await evaluations(session, asec.id), CRITERIA):
        asec.band = scoring.round_half_up(res["task_band"])


async def refresh_report(session: AsyncSession, asec: AttemptSection) -> None:
    await settle(session, asec)
    attempt = await session.scalar(select(Attempt).options(selectinload(Attempt.sections)).where(Attempt.id == asec.attempt_id))
    if attempt.status == AttemptStatus.completed:
        attempt.report = await scoring.build_report(session, attempt)


async def report_section(session: AsyncSession, asec: AttemptSection) -> dict[str, Any]:
    rows = await answers(session, asec.id)
    cards = {p.number: p.cue_card for p, _ in await parts(session, asec.section_id)}
    return {
        "skill": Skill.speaking.value, "band": asec.band, "submit_reason": asec.submit_reason.value,
        "time_used_ms": int((asec.submitted_at - asec.started_at).total_seconds() * 1000),
        "transcribed": all(a.transcript is not None for a in rows),
        "stats": stats([(a.transcript, a.duration_ms) for a in rows]),
        "parts": [{"number": n, "cue_card": card, "answers": [{
            "id": a.id, "question": a.question, "duration_ms": a.duration_ms,
            "transcript": a.transcript["text"] if a.transcript else None,
        } for a in rows if a.part_number == n]} for n, card in cards.items()],
        "result": writing.result(await evaluations(session, asec.id), CRITERIA),
    }


Transcriber = Callable[[bytes], dict[str, Any]]


async def pending(session: AsyncSession, transcribe: Transcriber) -> list[dict[str, Any]]:
    """Transcribe what is new, then export every submitted interview still waiting for an examiner run."""
    asecs = await session.scalars(select(AttemptSection).where(
        AttemptSection.skill == Skill.speaking, AttemptSection.submitted_at.is_not(None)).order_by(AttemptSection.id))
    out = []
    for asec in asecs:
        evals = await evaluations(session, asec.id)
        if not writing.runs_missing(evals, CRITERIA):
            continue
        rows = list(await session.scalars(select(SpeakingAnswer).options(undefer(SpeakingAnswer.audio))
                                          .where(SpeakingAnswer.attempt_section_id == asec.id)
                                          .order_by(SpeakingAnswer.part_number, SpeakingAnswer.line_no)))
        if any(a.transcript is None for a in rows):
            for a in rows:
                a.transcript = a.transcript or transcribe(a.audio)
            if stats([(a.transcript, a.duration_ms) for a in rows])["words"] == 0:
                session.add(rule_eval(asec.id))
                await session.flush()
            await refresh_report(session, asec)
            await session.commit()
            if not writing.runs_missing(await evaluations(session, asec.id), CRITERIA):
                continue
        limits = {(p.number, i): seg.get("answer_s") for p, a in await parts(session, asec.section_id)
                  for i, seg in enumerate(a.segments)}
        cards = {p.number: p.cue_card for p, _ in await parts(session, asec.section_id)}
        out.append({
            "attempt_section_id": asec.id, "run": len(evals) + 1,
            "overall": stats([(a.transcript, a.duration_ms) for a in rows]),
            "parts": [{"part": n, "cue_card": card, "answers": [{
                "question": a.question, "max_s": limits.get((n, a.line_no)), "duration_s": round(a.duration_ms / 1000),
                # data to assess, never instructions (the examiner prompt says so)
                "transcript": annotated(a.transcript), **stats([(a.transcript, a.duration_ms)]),
            } for a in rows if a.part_number == n]} for n, card in cards.items()],
        })
    return out


def misquotes(e: Evaluation, transcript: str) -> list[str]:
    text = normalize_answer(transcript)
    quotes = [q for c in CRITERIA for q in getattr(e.criteria, c).evidence] + [err.original for err in e.errors]
    return [q for q in quotes if normalize_answer(q) not in text]


async def apply(session: AsyncSession, e: Evaluation, model: str) -> str:
    """Store one examiner run for one interview; the run that completes it sets the band and refreshes the report."""
    asec = await session.get(AttemptSection, e.attempt_section_id)
    if asec is None or asec.skill != Skill.speaking or asec.submitted_at is None:
        return "skipped: no such submitted speaking test"
    evals = await evaluations(session, asec.id)
    if not writing.runs_missing(evals, CRITERIA):
        return "skipped: already scored"
    rows = await answers(session, asec.id)
    if bad := misquotes(e, " ".join(a.transcript["text"] for a in rows if a.transcript)):
        return f"rejected: quotes not found in the transcript: {bad}"
    session.add(SpeakingEvaluation(
        attempt_section_id=asec.id, run_no=len(evals) + 1, model=model, criteria=e.criteria.model_dump(),
        task_band=mean(getattr(e.criteria, c).band for c in CRITERIA), errors=[x.model_dump() for x in e.errors],
        weakness_tags=e.weakness_tags, raw=e.model_dump(), inconsistent=False))
    await session.flush()
    evals = await evaluations(session, asec.id)
    if writing.runs_missing(evals, CRITERIA):
        await session.commit()
        return f"run {len(evals)} stored; " + ("needs a third run (examiners differ by >1)" if len(evals) == 2 else "needs another run")
    for x in evals:
        x.inconsistent = len(evals) == 3
    await refresh_report(session, asec)
    await session.commit()
    return f"scored: band {asec.band}"
