import pytest

from app.services.normalize import count_words, normalize_answer


@pytest.mark.parametrize("text, n", [
    ("winter", 1),
    ("check-in", 1),  # hyphenated = one word (official rule)
    ("the check-in desk", 3),
    ("1.20 metres", 2),
    ("three hundred and twenty", 1),  # a number in words counts as one
    ("three hundred and twenty people", 2),
    ("bread and butter", 3),  # "and" between ordinary words still counts
    ("  19th   century ", 2),
    ("twenty-five", 1),
    ("", 0),
])
def test_count_words(text, n):
    assert count_words(text) == n


@pytest.mark.parametrize("raw, expected", [
    ("  The   River. ", "the river"),
    ("check–in", "check-in"),  # en dash unified
    ("O’Brien", "o'brien"),  # curly apostrophe unified
])
def test_normalize_answer(raw, expected):
    assert normalize_answer(raw) == expected
