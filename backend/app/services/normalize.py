"""Answer text rules (RESEARCH §3.4) and deterministic error classes (PLAN §4.2)."""

import difflib
import re

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("“"): '"', ord("”"): '"'}
_NUMBER_WORDS = set(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion".split()
)


def normalize_answer(text: str) -> str:
    """Case-insensitive, whitespace-collapsed, unified dashes/quotes, no trailing full stop."""
    text = text.translate(_DASHES).translate(_QUOTES).lower()
    return re.sub(r"\s+", " ", text).strip().rstrip(".").strip()


def count_words(text: str) -> int:
    """IELTS counting: a hyphenated word is one word; a number (figures or words, e.g.
    'three hundred and twenty') is one word."""
    tokens = normalize_answer(text).split()
    count, in_number = 0, False
    for i, tok in enumerate(tokens):
        word = tok.strip(",;:")
        is_num_word = all(part in _NUMBER_WORDS for part in word.split("-")) and word != ""
        # "and" between two number words is part of the number ("three hundred and twenty")
        joins_number = word == "and" and in_number and i + 1 < len(tokens) and tokens[i + 1].split("-")[0] in _NUMBER_WORDS
        if is_num_word or joins_number:
            if not in_number:
                count += 1
            in_number = True
        else:
            count += 1
            in_number = False
    return count


# ---------- error classes (PLAN §4.2) ----------

_SHORT = {"TRUE": "T", "FALSE": "F", "NOT GIVEN": "NG", "YES": "Y", "NO": "N"}


def _plural_variants(text: str) -> set[str]:
    return {text + "s", text + "es", text.removesuffix("es"), text.removesuffix("s")} - {text}


def classify_text(answer: str | None, accepted: list[str], max_words: int | None) -> str | None:
    """Gap-fill answer → None when correct, else its error class. The first matching rule wins."""
    a = normalize_answer(answer or "")
    variants = {normalize_answer(v) for v in accepted}
    if not a:
        return "blank"
    if max_words is not None and count_words(a) > max_words:
        return "word_limit"  # wrong even if the words are right, as in the real test
    if a in variants:
        return None
    if _plural_variants(a) & variants:
        return "plural_singular"
    if len(a) >= 4 and any(difflib.SequenceMatcher(None, a, v).ratio() >= 0.8 for v in variants):
        return "spelling"
    return "wrong_word"


def classify_choice(answer: str | None, accepted: list[str], qtype: str) -> str | None:
    """Letter / TRUE-FALSE-NOT GIVEN answer → None when correct, else its error class."""
    a = (answer or "").strip().upper()
    if not a:
        return "blank"
    if a in {k.strip().upper() for k in accepted}:
        return None
    if qtype in ("tfng", "ynng"):  # record the confusion, e.g. tfng:NG→F
        return f"{qtype}:{_SHORT.get(accepted[0].upper(), accepted[0])}→{_SHORT.get(a, a)}"
    return "wrong_option"
