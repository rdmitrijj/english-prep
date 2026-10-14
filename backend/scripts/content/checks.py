"""Deterministic content checks (PLAN §6.9 step 3). Each returns human-readable error strings; [] = pass."""

from app.models.enums import QType, Skill, TestKind
from app.services.normalize import count_words, normalize_answer
from scripts.content.schema import CGroup, CPart, CTest, PassageDraft
from scripts.content.spec import ORDERED_TYPES, READING_TOTAL_WORDS, READING_WORDS, TEXT_TYPES, letters

TFNG = {"TRUE", "FALSE", "NOT GIVEN"}
YNNG = {"YES", "NO", "NOT GIVEN"}


def check_test(test: CTest, word_range: tuple[int, int] = READING_WORDS) -> list[str]:
    errors: list[str] = []
    for section in test.sections:
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


def check_group(g: CGroup, labels: list[str], paragraphs: dict[str, str], full_text: str) -> list[str]:
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
    if g.qtype in ORDERED_TYPES and len(positions) == len(qs) and positions != sorted(positions):
        errors.append("questions must follow the order of the passage")

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
            for q in qs:
                opts = [o.letter for o in q.options or []]
                if opts != letters(4):
                    err(q, f"needs options A–D, got {opts}")
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
                    err(q, f"first answer {q.answer[0]!r} must appear verbatim in the passage")
                if not g.allow_number and any(ch.isdigit() for ch in q.answer[0]):
                    err(q, f"answer {q.answer[0]!r} contains a number but the rubric allows words only")

    # --- layouts carry one gap marker per question ---
    if g.qtype in (QType.summary_completion, QType.note_completion, QType.table_completion, QType.flowchart_completion):
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
