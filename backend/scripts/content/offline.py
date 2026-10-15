"""Reading content without an API key: Claude Code writes content/tests/<slug>.json by hand,
a separate agent blind-solves the candidate view, and this script does everything else.

    python -m scripts.content.offline check mock-01      # exact rubrics + all checks (exit 1 on errors)
    python -m scripts.content.offline view mock-01       # what the candidate sees — the blind solver's only input
    python -m scripts.content.offline finalize mock-01   # compare with content/verify/mock-01.json, set status

content/verify/<slug>.json holds the blind solver's answers: {"answers": [{number, answer, confidence, note}]}.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.models.enums import QType
from scripts.content.checks import check_test
from scripts.content.generate import assemble_groups, finalize, save, tests_dir
from scripts.content.prompts import PROMPT_VERSION
from scripts.content.schema import CTest, GroupsDraft, VerifierAnswers
from scripts.content.spec import GroupSpec
from scripts.content.verify import candidate_view, compare


def load(slug: str) -> CTest:
    return CTest.model_validate_json((tests_dir() / f"{slug}.json").read_text())


def set_rubrics(test: CTest) -> CTest:
    """Rubric wording (and matching-information options) always comes from spec.py, never from the author."""
    for part in (p for s in test.sections for p in s.parts):
        specs = [GroupSpec(g.qtype, len(g.questions), g.max_words, g.allow_number, pick=g.pick,
                           from_list=g.qtype == QType.summary_completion and bool(g.options)) for g in part.groups]
        first = part.groups[0].questions[0].number
        part.groups = assemble_groups(GroupsDraft(groups=part.groups), specs, part.passage, part.number, first)
    return test


def apply_answers(test: CTest, answers: VerifierAnswers) -> CTest:
    by_number = {a.number: a for a in answers.answers}
    for g in (g for s in test.sections for p in s.parts for g in p.groups):
        for q in g.questions:
            q.review = compare(g, q, by_number.get(q.number))
    test.generator_meta = {"prompt_version": PROMPT_VERSION, "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                           "models": {"generate": "claude-code", "verify": "claude-code blind subagent"}}
    return finalize(test)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.content.offline")
    parser.add_argument("cmd", choices=["check", "view", "finalize"])
    parser.add_argument("slug")
    args = parser.parse_args()
    test = set_rubrics(load(args.slug))

    if args.cmd == "view":
        for part in (p for s in test.sections for p in s.parts):
            print(candidate_view(part), end="\n\n")
        return
    if args.cmd == "check":
        test.check_errors = check_test(test)
    else:
        answers_path = Path(get_settings().content_dir) / "verify" / f"{args.slug}.json"
        apply_answers(test, VerifierAnswers.model_validate_json(answers_path.read_text()))
    save(test)
    print(f"{test.status.value}: {args.slug}  ({len(list(test.questions()))} questions, {len(test.check_errors)} check errors)")
    for e in test.check_errors:
        print("  check:", e)
    for q in test.questions():
        if q.review:
            print(f"  Q{q.number} {q.review.reason}: key {q.answer}, verifier {q.review.verifier_answer}")
    sys.exit(1 if test.check_errors else 0)


if __name__ == "__main__":
    main()
