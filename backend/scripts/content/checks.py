"""Deterministic content checks (PLAN §6.9 step 3). Each returns human-readable error strings; [] = pass."""

from pathlib import Path

from app.config import get_settings
from app.models.enums import QType, Skill, TestKind
from app.services.normalize import count_words, normalize_answer
from scripts.content.schema import CGroup, CPart, CTest, PassageDraft
from scripts.content.spec import (
    LINE_GAP_S, LISTENING_AUDIO_MIN, LISTENING_CONTEXTS, ORDERED_TYPES, READING_TOTAL_WORDS, READING_WORDS, SPEAKING_ANSWER_S,
    SPEAKING_DEADLINE_S, SPEAKING_QUESTIONS, SPEECH_WPS, TEXT_TYPES, WRITING_TOPICS, letters,
)

TFNG = {"TRUE", "FALSE", "NOT GIVEN"}
YNNG = {"YES", "NO", "NOT GIVEN"}


def check_test(test: CTest, word_range: tuple[int, int] = READING_WORDS) -> list[str]:
    errors: list[str] = []
    for section in test.sections:
        if section.skill == Skill.listening:
            errors += check_listening_section(section, test.kind)
            continue
        if section.skill == Skill.writing:
            errors += check_writing_section(section, test.kind)
            continue
        if section.skill == Skill.speaking:
            errors += check_speaking_section(section)
            continue
        if section.skill != Skill.reading:
            continue
        numbers = [q.number for p in section.parts for g in p.groups for q in g.questions]
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"reading: question numbers must run 1..n without gaps, got {numbers}")
        if test.kind == TestKind.mock:
            if len(section.parts) != 3 or len(numbers) != 40:
                errors.append(f"reading mock: need 3 passages and 40 questions, got {len(section.parts)} / {len(numbers)}")
            total = sum(count_words(par.text) for p in section.parts if p.passage for par in p.passage.paragraphs)
            if not READING_TOTAL_WORDS[0] <= total <= READING_TOTAL_WORDS[1]:
                errors.append(f"reading mock: total {total} words outside {READING_TOTAL_WORDS}")
        for part in section.parts:
            errors += [f"P{part.number} {e}" for e in check_reading_part(part, word_range)]
    return errors


def check_writing_section(section, kind: TestKind) -> list[str]:
    errors: list[str] = []
    numbers = [p.number for p in section.parts]
    if kind == TestKind.mock and (numbers != [1, 2] or section.duration_s != 3600):
        errors.append(f"writing mock: need Task 1 and Task 2 in 60 minutes, got parts {numbers}, {section.duration_s} s")
    for part in section.parts:
        errors += [f"W{part.number} {e}" for e in check_writing_part(part)]
    return errors


def check_writing_part(part: CPart) -> list[str]:
    w = part.writing
    if w is None:
        return ["missing writing task"]
    errors = []
    if part.groups:
        errors.append("a writing part has no question groups")
    if w.task_number != part.number:
        errors.append(f"task_number {w.task_number} must equal the part number")
    if part.topic not in WRITING_TOPICS:
        errors.append(f"topic must be one of {sorted(WRITING_TOPICS)}, got {part.topic!r}")
    if not w.prompt.strip() or "at least" in w.prompt.lower():
        errors.append("prompt must hold only the task's own text (the rubric lines are added automatically)")
    if w.task_number == 2:
        if w.essay_type is None or w.visual is not None:
            errors.append("Task 2 needs an essay_type and no visual")
        return errors
    v = w.visual
    if v is None or w.essay_type is not None:
        return errors + ["Task 1 needs a visual and no essay_type"]
    drawn = v.type in ("process", "map")
    if drawn and (v.charts or not (v.description or "").strip()):
        errors.append(f"a {v.type} needs a description and no charts")
    if not drawn and len(v.charts) != (2 if v.type == "mixed" else 1):
        errors.append(f"a {v.type} visual needs {2 if v.type == 'mixed' else 1} chart(s), got {len(v.charts)}")
    if not drawn and v.type != "mixed" and v.charts and v.charts[0].type != v.type:
        errors.append(f"visual type {v.type} but chart type {v.charts[0].type}")
    for c in v.charts:
        if not c.series or any(len(sr.values) != len(c.categories) for sr in c.series):
            errors.append(f"chart {c.title!r}: every series needs one value per category ({len(c.categories)})")
        if c.type == "pie" and any(not 99 <= sum(sr.values) <= 101 for sr in c.series):
            errors.append(f"pie {c.title!r}: each pie must add up to 100")
    if v.url is None:
        errors.append("visual not drawn yet (python -m scripts.content.visuals render <slug>)")
    elif not (Path(get_settings().content_dir) / v.url.removeprefix("/")).exists():
        errors.append(f"visual file missing: {v.url}")
    return errors


def check_speaking_section(section) -> list[str]:
    errors: list[str] = []
    if [p.number for p in section.parts] != [1, 2, 3] or section.duration_s != SPEAKING_DEADLINE_S:
        errors.append(f"speaking: need parts 1–3 and duration_s {SPEAKING_DEADLINE_S}")
    for part in section.parts:
        errors += [f"S{part.number} {e}" for e in check_speaking_part(part)]
    return errors


def check_speaking_part(part: CPart) -> list[str]:
    if part.script is None:
        return ["missing script (the examiner's lines)"]
    errors: list[str] = []
    if [s.id for s in part.script.speakers] != ["examiner"] or part.groups:
        errors.append("one speaker, 'examiner', and no question groups")
    if (part.cue_card is None) != (part.number != 2) or (part.cue_card and len(part.cue_card.bullets) not in (3, 4)):
        errors.append("Part 2, and only Part 2, has a cue card with 3–4 bullets")
    asks = [ln for ln in part.script.lines if ln.answer_s]
    lo, hi = SPEAKING_QUESTIONS[part.number]
    if not lo <= len(asks) <= hi:
        errors.append(f"{len(asks)} questions, expected {lo}–{hi}")
    a_lo, a_hi = SPEAKING_ANSWER_S[part.number]
    errors += [f"line {i}: answer_s {ln.answer_s} outside {a_lo}–{a_hi}" for i, ln in enumerate(part.script.lines)
               if ln.answer_s and not (a_lo <= ln.answer_s <= a_hi or (part.number == 2 and ln.answer_s <= 45))]
    if part.number == 2 and (not asks or asks[0].answer_s != 120):
        errors.append("the first answered line of Part 2 is the long turn (answer_s 120)")
    if part.audio and len(part.audio.segments) != len(part.script.lines):
        errors.append("audio is out of date with the script: render it again")
    return errors


def check_passage(passage: PassageDraft, word_range: tuple[int, int], min_paragraphs: int = 4) -> list[str]:
    errors: list[str] = []
    labels = [p.label for p in passage.paragraphs]
    if labels != letters(len(labels)) or len(labels) < min_paragraphs:
        errors.append(f"paragraph labels must be A, B, C… (≥{min_paragraphs}), got {labels}")
    words = sum(count_words(p.text) for p in passage.paragraphs)
    if not word_range[0] <= words <= word_range[1]:
        errors.append(f"passage has {words} words, expected {word_range}")
    return errors


def check_reading_part(part: CPart, word_range: tuple[int, int]) -> list[str]:
    if part.passage is None:
        return ["missing passage"]
    errors = check_passage(part.passage, word_range)
    labels = [p.label for p in part.passage.paragraphs]
    paragraphs = {p.label: normalize_answer(p.text) for p in part.passage.paragraphs}
    full_text = " ".join(paragraphs.values())
    for group in part.groups:
        errors += [f"{group.qtype} {e}" for e in check_group(group, labels, paragraphs, full_text)]
    return errors


def estimated_seconds(part: CPart) -> float:
    lines = part.script.lines if part.script else []
    return sum(count_words(line.text) / SPEECH_WPS + LINE_GAP_S + line.pause_after_s for line in lines)


def check_listening_section(section, kind: TestKind) -> list[str]:
    errors: list[str] = []
    numbers = [q.number for p in section.parts for g in p.groups for q in g.questions]
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append(f"listening: question numbers must run 1..n without gaps, got {numbers}")
    if kind == TestKind.mock:
        if [p.number for p in section.parts] != [1, 2, 3, 4] or len(numbers) != 40:
            errors.append(f"listening mock: need parts 1–4 and 40 questions, got {len(section.parts)} / {len(numbers)}")
        minutes = sum(estimated_seconds(p) for p in section.parts) / 60
        if not LISTENING_AUDIO_MIN[0] <= minutes <= LISTENING_AUDIO_MIN[1]:
            errors.append(f"listening mock: about {minutes:.1f} min of audio, expected {LISTENING_AUDIO_MIN} (+2 min review)")
        accents = {s.accent for p in section.parts if p.script for s in p.script.speakers if s.id != "narrator"}
        if len(accents) < 3:
            errors.append(f"listening mock: use at least 3 accents across the parts, got {sorted(accents)}")
    for part in section.parts:
        errors += [f"L{part.number} {e}" for e in check_listening_part(part)]
    return errors


# How many voices (narrator excluded) each context needs: (min, max).
CAST = {"social_dialogue": (2, 2), "social_monologue": (1, 2), "academic_discussion": (2, 4), "academic_lecture": (1, 1)}


def check_listening_part(part: CPart) -> list[str]:
    if part.script is None:
        return ["missing script"]
    errors: list[str] = []
    ids = [s.id for s in part.script.speakers]
    if "narrator" not in ids:
        errors.append("needs a narrator speaker for the rubric announcements")
    if part.context not in LISTENING_CONTEXTS:
        errors.append(f"context must be one of {LISTENING_CONTEXTS}, got {part.context!r}")
    else:
        cast = {line.speaker for line in part.script.lines} - {"narrator"}
        lo, hi = CAST[part.context]
        if not lo <= len(cast) <= hi:
            errors.append(f"{part.context} needs {lo}–{hi} speakers besides the narrator, got {len(cast)}")
    for i, line in enumerate(part.script.lines):
        if line.speaker not in ids:
            errors.append(f"line {i}: unknown speaker {line.speaker!r}")
        if not line.text.strip():
            errors.append(f"line {i}: empty text")
    if part.audio and len(part.audio.segments) != len(part.script.lines):
        errors.append("audio is out of date with the script: render it again")
    # The checks below reuse the Reading rules with each script line as a "paragraph" keyed by its index.
    lines = {str(i): normalize_answer(line.text) for i, line in enumerate(part.script.lines)}
    full_text = " ".join(lines.values())
    for group in part.groups:
        errors += [f"{group.qtype} {e}" for e in check_group(group, list(lines), lines, full_text, listening=True)]
    return errors


def check_group(g: CGroup, labels: list[str], paragraphs: dict[str, str], full_text: str, listening: bool = False) -> list[str]:
    errors: list[str] = []
    qs = g.questions
    group_letters = [o.letter for o in g.options or []]

    def err(q, msg):
        errors.append(f"Q{q.number}: {msg}")

    # --- evidence must be quoted verbatim, and ordered types must follow the text ---
    positions = []
    for q in qs:
        par = paragraphs.get(q.evidence.paragraph)
        quote = normalize_answer(q.evidence.quote)
        if par is None:
            err(q, f"evidence paragraph {q.evidence.paragraph!r} does not exist")
        elif not quote or quote not in par:
            err(q, f"evidence quote not found verbatim in paragraph {q.evidence.paragraph}: {q.evidence.quote[:60]!r}")
        else:
            positions.append((labels.index(q.evidence.paragraph), par.index(quote)))
        if not q.explanation.correct.strip():
            err(q, "empty explanation")
    # Listening questions always follow the recording (RESEARCH §2.1); in Reading only some types do.
    if (listening or g.qtype in ORDERED_TYPES) and len(positions) == len(qs) and positions != sorted(positions):
        errors.append("questions must follow the order of the " + ("recording" if listening else "passage"))

    # --- answer validity per type ---
    single = [q.answer[0].upper() if len(q.answer) == 1 else None for q in qs]
    match g.qtype:
        case QType.tfng | QType.ynng:
            allowed = TFNG if g.qtype == QType.tfng else YNNG
            for q, a in zip(qs, single):
                if a not in allowed:
                    err(q, f"answer must be one of {sorted(allowed)}, got {q.answer}")
            if len(qs) >= 4 and len(set(single)) < 2:
                errors.append("answers are all the same")
            if len(qs) >= 5 and "NOT GIVEN" not in single:
                errors.append("no NOT GIVEN item in a group of 5+")
        case QType.mcq if g.pick > 1:
            if len(qs) != g.pick or len(group_letters) < g.pick + 2:
                errors.append(f"multi-answer MCQ needs {g.pick} questions and ≥{g.pick + 2} shared options")
            key = sorted(qs[0].answer) if qs else []
            for q in qs:
                if sorted(q.answer) != key or len(key) != g.pick or not set(key) <= set(group_letters):
                    err(q, f"each question must carry the same {g.pick} correct letters from the options, got {q.answer}")
        case QType.mcq:
            n_opts = 3 if listening else 4  # Listening MCQ has A–C (RESEARCH §3.1)
            for q in qs:
                opts = [o.letter for o in q.options or []]
                if opts != letters(n_opts):
                    err(q, f"needs options A–{letters(n_opts)[-1]}, got {opts}")
                if len(q.answer) != 1 or q.answer[0] not in opts:
                    err(q, f"answer must be one option letter, got {q.answer}")
        case QType.matching_information:
            for q, a in zip(qs, single):
                if a not in labels:
                    err(q, f"answer must be a paragraph letter, got {q.answer}")
        case QType.matching_headings:
            if len(group_letters) < len(qs) + 2:
                errors.append(f"need ≥{len(qs) + 2} headings for {len(qs)} paragraphs, got {len(group_letters)}")
            answers = [q.answer[0] if len(q.answer) == 1 else None for q in qs]
            for q, a in zip(qs, answers):
                if a not in group_letters:
                    err(q, f"answer must be a heading numeral from the list, got {q.answer}")
            if len(set(answers)) != len(answers):
                errors.append("a heading is used more than once")
        case QType.matching:
            if len(group_letters) < len(qs) + 1:
                errors.append(f"need ≥{len(qs) + 1} options in the box, got {len(group_letters)}")
            for q, a in zip(qs, single):
                if a not in group_letters:
                    err(q, f"answer must be an option letter, got {q.answer}")
        case QType.matching_features | QType.matching_sentence_endings:
            min_opts = 3 if g.qtype == QType.matching_features else len(qs) + 2
            if len(group_letters) < min_opts:
                errors.append(f"need ≥{min_opts} options, got {len(group_letters)}")
            for q, a in zip(qs, single):
                if a not in group_letters:
                    err(q, f"answer must be an option letter, got {q.answer}")
            if g.qtype == QType.matching_sentence_endings and len(set(single)) != len(single):
                errors.append("an ending is used more than once")
        case QType.summary_completion if g.options:
            if len(group_letters) < len(qs) + 3:
                errors.append(f"word list needs ≥{len(qs) + 3} options, got {len(group_letters)}")
            for q, a in zip(qs, single):
                if a not in group_letters:
                    err(q, f"answer must be a letter from the word list, got {q.answer}")
        case t if t in TEXT_TYPES:
            if not g.max_words:
                errors.append("text-answer group needs max_words")
            for q in qs:
                if not q.answer:
                    err(q, "no accepted answers")
                    continue
                for variant in q.answer:
                    if count_words(variant) > (g.max_words or 0):
                        err(q, f"answer {variant!r} exceeds {g.max_words} word(s)")
                if normalize_answer(q.answer[0]) not in full_text:
                    err(q, f"first answer {q.answer[0]!r} must appear verbatim in the " + ("recording" if listening else "passage"))
                if not g.allow_number and any(ch.isdigit() for ch in q.answer[0]):
                    err(q, f"answer {q.answer[0]!r} contains a number but the rubric allows words only")

    # --- layouts carry one gap marker per question ---
    if g.qtype in (QType.summary_completion, QType.note_completion, QType.table_completion, QType.flowchart_completion,
                   QType.form_completion):
        layout = g.layout
        text = ""
        if layout:
            text = (layout.template or "") + " ".join(layout.steps or [])
            if layout.table:
                text += " ".join(c for row in layout.table.rows for c in row)
        for q in qs:
            if f"{{{q.number}}}" not in text:
                err(q, f"gap marker {{{q.number}}} missing from the layout")
    if g.qtype == QType.sentence_completion:
        for q in qs:
            if "___" not in q.prompt:
                err(q, "sentence must contain a gap (___)")
    return errors
