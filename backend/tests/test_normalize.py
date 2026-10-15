import pytest

from app.services.normalize import classify_choice, classify_text, count_words, normalize_answer


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


@pytest.mark.parametrize("answer, accepted, max_words, expected", [
    ("", ["winter"], 1, "blank"),
    ("  ", ["winter"], 1, "blank"),
    ("cold winter", ["winter"], 1, "word_limit"),  # over the limit even though it contains the key
    ("The Winter.", ["the winter", "winter"], 2, None),  # case, full stop
    ("beechwoods", ["beech woods", "beechwoods"], 2, None),  # explicit variant
    ("check–in desk", ["check-in desk"], 2, None),  # dash unified; hyphenated word counts once
    ("24 hours", ["24 hours", "twenty-four hours"], 2, None),
    ("tubes", ["tube"], 1, "plural_singular"),
    ("boxes", ["box"], 1, "plural_singular"),
    ("nutriton", ["nutrition"], 1, "spelling"),
    ("colour", ["color"], 1, "spelling"),  # UK/US only via the explicit list → still wrong
    ("cat", ["car"], 1, "wrong_word"),  # under 4 letters: never a "spelling" error
    ("predators", ["prey"], 1, "wrong_word"),
])
def test_classify_text(answer, accepted, max_words, expected):
    assert classify_text(answer, accepted, max_words) == expected


@pytest.mark.parametrize("answer, accepted, qtype, expected", [
    ("b", ["B"], "mcq", None),
    ("C", ["B"], "mcq", "wrong_option"),
    (None, ["B"], "matching_headings", "blank"),
    ("NOT GIVEN", ["FALSE"], "tfng", "tfng:F→NG"),
    ("FALSE", ["NOT GIVEN"], "tfng", "tfng:NG→F"),
    ("YES", ["NO"], "ynng", "ynng:N→Y"),
    ("TRUE", ["TRUE"], "tfng", None),
])
def test_classify_choice(answer, accepted, qtype, expected):
    assert classify_choice(answer, accepted, qtype) == expected
