"""Blind solve (PLAN §6.9 step 4): a different model sees only what a candidate sees and answers everything.
Any disagreement or low confidence marks the question for human review."""

from app.config import get_settings
from app.models.enums import QType
from app.services import llm
from app.services.normalize import normalize_answer
from scripts.content.prompts import VERIFY_SYSTEM
from scripts.content.schema import CGroup, CPart, CQuestion, Review, VerifierAnswer, VerifierAnswers

MIN_CONFIDENCE = 0.7
TEXT_ANSWER = {QType.sentence_completion, QType.note_completion, QType.table_completion, QType.form_completion,
               QType.flowchart_completion, QType.short_answer, QType.summary_completion}


def candidate_view(part: CPart) -> str:
    """Render a part as the candidate sees it — no answers, explanations or evidence."""
    out = []
    if part.script:  # the blind solver can't listen, so it reads exactly what is spoken
        roles = {sp.id: sp.role for sp in part.script.speakers}
        out.append(f"LISTENING PART {part.number}: the candidate hears this recording ONCE (transcript):\n")
        out += [f"[{roles[ln.speaker]}] {ln.text}" for ln in part.script.lines]
    if part.passage:
        out.append(f"READING PASSAGE: {part.passage.title}\n")
        out += [f"[{p.label}] {p.text}\n" for p in part.passage.paragraphs]
        if part.passage.glossary:
            out.append("Glossary: " + "; ".join(f"{g.term}: {g.definition}" for g in part.passage.glossary) + "\n")
    for g in part.groups:
        nums = [q.number for q in g.questions]
        out.append(f"\nQuestions {nums[0]}–{nums[-1]}\n{g.instructions}")
        if g.layout:
            if g.layout.title:
                out.append(g.layout.title)
            if g.layout.template:
                out.append(g.layout.template)
            if g.layout.table:
                out.append(" | ".join(g.layout.table.columns))
                out += [" | ".join(r) for r in g.layout.table.rows]
            if g.layout.steps:
                out.append("\n↓\n".join(g.layout.steps))
        if g.options and g.qtype != QType.matching_information:
            out += [f"{o.letter}  {o.text}" for o in g.options]
        for q in g.questions:
            out.append(f"{q.number}. {q.prompt}")
            out += [f"   {o.letter}  {o.text}" for o in q.options or []]
    return "\n".join(out)


def compare(group: CGroup, q: CQuestion, va: VerifierAnswer | None) -> Review | None:
    if va is None or not va.answer:
        return Review(reason="verifier gave no answer")
    if group.qtype in TEXT_ANSWER and not group.options:
        key = {normalize_answer(a) for a in q.answer}
        agrees = normalize_answer(va.answer[0]) in key
    else:  # letters, numerals, TRUE/FALSE/NOT GIVEN…
        agrees = sorted(a.strip().upper() for a in va.answer) == sorted(a.strip().upper() for a in q.answer)
    if not agrees:
        return Review(reason="verifier disagreed", verifier_answer=va.answer, confidence=va.confidence)
    if va.confidence < MIN_CONFIDENCE:
        return Review(reason=f"verifier unsure: {va.note}", verifier_answer=va.answer, confidence=va.confidence)
    return None


async def verify_part(part: CPart) -> int:
    """Sets `review` on each disputed question. Returns how many were flagged."""
    result = await llm.structured(
        purpose="content_verify", model=get_settings().llm_model_verify,
        system=VERIFY_SYSTEM, user=candidate_view(part), schema=VerifierAnswers, effort="high",
    )
    by_number = {a.number: a for a in result.answers}
    flagged = 0
    for g in part.groups:
        for q in g.questions:
            q.review = compare(g, q, by_number.get(q.number))
            flagged += q.review is not None
    return flagged
