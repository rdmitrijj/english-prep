"""Answer text rules from RESEARCH §3.4. M3 adds error classification on top of these."""

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
