import pytest

from app.models.enums import QType
from scripts.content.checks import check_test
from scripts.content.spec import MOCK_READING, GroupSpec, instructions
from tests.content_fixture import make

RELAXED = (10, 2000)


def errors_after(mutate) -> list[str]:
    t = make()
    mutate(t.sections[0].parts[0])
    return check_test(t, word_range=RELAXED)


def test_good_fixture_passes():
    assert check_test(make(), word_range=RELAXED) == []


@pytest.mark.parametrize("mutate, expected", [
    (lambda p: setattr(p.groups[0].questions[0].evidence, "quote", "kept by people for nine thousand years"),
     "not found verbatim"),
    (lambda p: setattr(p.groups[0].questions[0], "answer", ["MAYBE"]), "must be one of"),
    (lambda p: setattr(p.groups[1].questions[0], "answer", ["each cold winter"]), "exceeds 1 word"),
    (lambda p: setattr(p.groups[1].questions[1], "answer", ["food"]), "verbatim in the passage"),
    (lambda p: setattr(p.groups[3].questions[1], "answer", ["ii"]), "used more than once"),
    (lambda p: setattr(p.groups[1].layout, "template", "- happen mainly in {4}"), "gap marker {5} missing"),
    (lambda p: p.groups[0].questions.reverse(), "order of the passage"),
    (lambda p: setattr(p.groups[3].questions[1], "number", 9), "without gaps"),
    (lambda p: setattr(p.groups[2].questions[0], "options", p.groups[2].questions[0].options[:3]), "options A–D"),
    (lambda p: setattr(p.groups[2].questions[0], "answer", ["E"]), "one option letter"),
    (lambda p: setattr(p.groups[0].questions[0].evidence, "paragraph", "Z"), "does not exist"),
    (lambda p: p.passage.paragraphs.pop(), "paragraph labels"),
])
def test_each_check_catches_its_defect(mutate, expected):
    errors = errors_after(mutate)
    assert any(expected in e for e in errors), errors


def test_strict_word_range_rejects_short_passage():
    assert any("passage has" in e for e in check_test(make()))


def test_mock_blueprints_have_three_passages_and_forty_questions():
    for slug, specs in MOCK_READING.items():
        assert len(specs) == 3, slug
        assert sum(s.count for s in specs) == 40, slug
        assert [s.level for s in specs] == ["easier", "medium", "harder"], slug


def test_every_reading_type_has_a_rubric():
    reading_types = set(QType) - {QType.matching, QType.form_completion, QType.map_labelling, QType.diagram_labelling}
    for qtype in reading_types:
        g = GroupSpec(qtype, 4, max_words=2, allow_number=True)
        assert instructions(g, 1, 4, 1, 6, 7)
    assert "NO MORE THAN TWO WORDS AND/OR A NUMBER" in instructions(GroupSpec(QType.sentence_completion, 3, 2, True), 1, 3, 1, 6, 0)
    assert "Choose TWO letters, A–E." == instructions(GroupSpec(QType.mcq, 2, pick=2), 1, 2, 1, 6, 5)
