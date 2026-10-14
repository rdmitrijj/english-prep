"""A tiny hand-written reading test that passes every check (with relaxed word limits)."""

from scripts.content.schema import CTest

PASSAGE = {
    "title": "Keeping bees",
    "paragraphs": [
        {"label": "A", "text": "The honeybee has been kept by humans for at least nine thousand years. "
                               "Early beekeepers used hollow logs and clay pots as hives."},
        {"label": "B", "text": "In the nineteenth century, Lorenzo Langstroth designed a hive with removable frames. "
                               "This allowed keepers to inspect colonies without destroying the comb."},
        {"label": "C", "text": "Today, many colonies are lost each winter. Researchers blame a combination of "
                               "parasites, pesticides and poor nutrition."},
        {"label": "D", "text": "Some scientists argue that urban rooftops offer bees a surprisingly varied diet, "
                               "although others doubt that cities can support large populations."},
    ],
    "glossary": [],
}


def q(number, prompt, answer, par, quote, options=None):
    return {
        "number": number, "prompt": prompt, "options": options, "answer": answer, "difficulty": 2,
        "sub_skill": "detail", "evidence": {"paragraph": par, "quote": quote},
        "explanation": {"correct": "Paraphrase of the evidence.", "distractors": []},
    }


def opts(*texts, roman=False):
    labels = "i ii iii iv v vi".split() if roman else "ABCDEF"
    return [{"letter": l, "text": t} for l, t in zip(labels, texts)]


def make() -> CTest:
    return CTest.model_validate({
        "slug": "fixture-bees", "kind": "practice", "title": "Keeping bees", "status": "published",
        "sections": [{"skill": "reading", "duration_s": None, "parts": [{
            "number": 1, "context": "academic_reading", "topic": "biology-ecology", "passage": PASSAGE,
            "groups": [
                {"qtype": "tfng", "instructions": "TFNG rubric", "options": None, "layout": None, "questions": [
                    q(1, "Humans began keeping bees less than five thousand years ago.", ["FALSE"], "A",
                      "kept by humans for at least nine thousand years"),
                    q(2, "Langstroth sold his design to manufacturers.", ["NOT GIVEN"], "B",
                      "Lorenzo Langstroth designed a hive with removable frames"),
                    q(3, "Langstroth's hive let keepers examine a colony without damaging it.", ["TRUE"], "B",
                      "inspect colonies without destroying the comb"),
                ]},
                {"qtype": "note_completion", "instructions": "Notes rubric", "max_words": 1, "options": None,
                 "layout": {"title": "Colony losses", "template": "- happen mainly in {4}\n- causes include poor {5}",
                            "table": None, "steps": None},
                 "questions": [
                     q(4, "losses happen mainly in …", ["winter"], "C", "many colonies are lost each winter"),
                     q(5, "causes include poor …", ["nutrition"], "C", "poor nutrition"),
                 ]},
                {"qtype": "mcq", "instructions": "MCQ rubric", "options": None, "layout": None, "questions": [
                    q(6, "What do some scientists claim about cities?", ["B"], "D",
                      "urban rooftops offer bees a surprisingly varied diet",
                      options=opts("They harm bees", "They provide a varied diet", "They have few flowers",
                                   "They support large populations")),
                ]},
                {"qtype": "matching_headings", "instructions": "Headings rubric",
                 "options": opts("Threats facing modern colonies", "An ancient practice", "A design breakthrough",
                                 "Bees in the city", roman=True),
                 "layout": None, "questions": [
                     q(7, "Paragraph A", ["ii"], "A", "Early beekeepers used hollow logs"),
                     q(8, "Paragraph B", ["iii"], "B", "designed a hive with removable frames"),
                 ]},
            ],
        }]}],
    })
