"""Human review of generated content that failed checks or the blind solve.

    python -m scripts.content.review           # go through every needs_review test interactively
    python -m scripts.content.review --list    # just list them

To fix an item, edit content/tests/<slug>.json in your editor (e.g. correct `answer`), then accept it here.
"""

import argparse
from pathlib import Path

from app.config import get_settings
from app.models.enums import ContentStatus
from scripts.content.schema import CTest
from scripts.content.generate import save


def describe(t: CTest) -> str:
    lines = [f"\n=== {t.slug}: {t.title}"]
    lines += [f"  check: {e}" for e in t.check_errors]
    for s in t.sections:
        for p in s.parts:
            for g in p.groups:
                for q in g.questions:
                    if q.review:
                        lines.append(f"  Q{q.number} [{g.qtype.value}] {q.prompt}")
                        lines.append(f"      key: {q.answer}   verifier: {q.review.verifier_answer} "
                                     f"(confidence {q.review.confidence})  — {q.review.reason}")
                        lines.append(f"      evidence [{q.evidence.paragraph}]: {q.evidence.quote}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.content.review")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    files = sorted((Path(get_settings().content_dir) / "tests").glob("*.json"))
    pending = [t for t in (CTest.model_validate_json(f.read_text()) for f in files) if t.status == ContentStatus.needs_review]
    if not pending:
        print("Nothing to review.")
    for t in pending:
        print(describe(t))
        if args.list:
            continue
        choice = input("[a]ccept as is / [r]eject / [s]kip? ").strip().lower()
        if choice == "a":
            for q in t.questions():
                q.review = None
            t.check_errors, t.status = [], ContentStatus.published
        elif choice == "r":
            t.status = ContentStatus.rejected
        else:
            continue
        save(t)
        print(f"  → {t.status.value}")


if __name__ == "__main__":
    main()
