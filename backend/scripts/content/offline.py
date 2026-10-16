"""Reading content without an API key: Claude Code writes content/tests/<slug>.json by hand,
a separate agent blind-solves the candidate view, and this script does everything else.

    python -m scripts.content.offline check mock-01      # exact rubrics + all checks (exit 1 on errors)
    python -m scripts.content.offline view mock-01       # what the candidate sees — the blind solver's only input
    python -m scripts.content.offline finalize mock-01   # compare with content/verify/mock-01.json, set status
    python -m scripts.content.offline merge mock-01 --file drafts/x.json   # add/replace one section (a CSection JSON)

content/verify/<slug>.json holds the blind solver's answers: {"answers": [{number, answer, confidence, note}]}.
A test with several sections numbers each one 1–40, so view/finalize take --skill and use verify/<slug>-<skill>.json.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.models.enums import QType, Skill
from app.services.normalize import normalize_answer
from scripts.content.checks import check_test
from scripts.content.generate import assemble_groups, finalize, save, tests_dir
from scripts.content.prompts import PROMPT_VERSION
from scripts.content.schema import CPart, CSection, CTest, GroupsDraft, VerifierAnswers
from scripts.content.spec import GroupSpec, listening_instructions
from scripts.content.verify import candidate_view, compare


def load(slug: str) -> CTest:
    return CTest.model_validate_json((tests_dir() / f"{slug}.json").read_text())


def set_rubrics(test: CTest) -> CTest:
    """Rubric wording (and matching-information options) always comes from spec.py, never from the author."""
    for part in (p for s in test.sections for p in s.parts):
        if part.script:
            listening_rubrics(part)
            continue
        if part.writing:  # its rubric is added at seed time (spec.writing_rubric)
            continue
        specs = [GroupSpec(g.qtype, len(g.questions), g.max_words, g.allow_number, pick=g.pick,
                           from_list=g.qtype == QType.summary_completion and bool(g.options)) for g in part.groups]
        first = part.groups[0].questions[0].number
        part.groups = assemble_groups(GroupsDraft(groups=part.groups), specs, part.passage, part.number, first)
    return test


def listening_rubrics(part: CPart) -> None:
    """Listening: exact rubrics, and each evidence quote linked to the script line that contains it."""
    lines = [normalize_answer(line.text) for line in part.script.lines]
    for g in part.groups:
        spec = GroupSpec(g.qtype, len(g.questions), g.max_words, g.allow_number, pick=g.pick)
        g.instructions = listening_instructions(spec, g.questions[0].number, g.questions[-1].number, len(g.options or []))
        for q in g.questions:
            quote = normalize_answer(q.evidence.quote)
            q.evidence.paragraph = next((str(i) for i, line in enumerate(lines) if quote and quote in line), "")


def apply_answers(test: CTest, answers: VerifierAnswers, skill: Skill | None = None) -> CTest:
    by_number = {a.number: a for a in answers.answers}
    for g in (g for s in test.sections if skill in (None, s.skill) for p in s.parts for g in p.groups):
        for q in g.questions:
            q.review = compare(g, q, by_number.get(q.number))
    verified = set(test.generator_meta.get("verified", [])) | ({skill} if skill else {s.skill for s in test.sections})
    test.generator_meta = {"prompt_version": PROMPT_VERSION, "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                           "models": {"generate": "claude-code", "verify": "claude-code blind subagent"},
                           "verified": sorted(verified)}
    return finalize(test)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.content.offline")
    parser.add_argument("cmd", choices=["check", "view", "finalize", "merge"])
    parser.add_argument("slug")
    parser.add_argument("--skill", type=Skill, help="only this section (view, finalize)")
    parser.add_argument("--file", help="merge: a CSection JSON file, relative to the content dir")
    args = parser.parse_args()
    content = Path(get_settings().content_dir)

    if args.cmd == "merge":
        section = CSection.model_validate_json((content / args.file).read_text())
        test = load(args.slug)
        test.sections = sorted([s for s in test.sections if s.skill != section.skill] + [section],
                               key=lambda s: list(Skill).index(s.skill))
        save(test)
        print(f"merged {section.skill} into {args.slug}; now run: check {args.slug}")
        return
    test = set_rubrics(load(args.slug))

    if args.cmd == "view":
        for part in (p for s in test.sections if args.skill in (None, s.skill) for p in s.parts):
            print(candidate_view(part), end="\n\n")
        return
    if args.cmd == "check" and all(s.skill == Skill.writing for s in test.sections):
        finalize(test)  # writing has no blind solve: passing the checks publishes it
    elif args.cmd == "check":
        test.check_errors = check_test(test)
    else:
        name = f"{args.slug}-{args.skill}" if args.skill else args.slug
        answers = VerifierAnswers.model_validate_json((content / "verify" / f"{name}.json").read_text())
        apply_answers(test, answers, args.skill)
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
