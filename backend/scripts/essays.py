"""Score essays with Claude Code instead of an in-app LLM (PLAN §6.7, M6 decision).

    python -m scripts.essays pending --out /tmp/pending.json   # essays still needing an examiner run
    python -m scripts.essays apply /tmp/run-a.json              # store one examiner's verdicts, one run per essay

The workflow (when the user says "score my essays"):
1. `pending` exports every submitted essay that still needs a run.
2. Two blind examiner agents each read scripts/essays_examiner.md + the export and write {"evaluations": [...]}.
3. `apply` each file; a pair that differs by more than one band on a criterion shows up in `pending` again
   for a third run. When an essay is complete, its section band and attempt report are updated.
Against production, run the same commands with DATABASE_URL pointing at Neon.
"""

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import BaseModel

from app.db import SessionLocal
from app.services import writing


class Batch(BaseModel):
    evaluations: list[writing.Evaluation]


async def pending(out: Path | None) -> None:
    async with SessionLocal() as session:
        essays = await writing.pending(session)
    text = json.dumps({"essays": essays}, indent=2, ensure_ascii=False)
    if out:
        out.write_text(text + "\n")
        print(f"{len(essays)} essays need a run → {out}")
    else:
        print(text)


async def apply(path: Path, model: str) -> None:
    batch = Batch.model_validate_json(path.read_text())
    for e in batch.evaluations:
        async with SessionLocal() as session:
            print(f"essay {e.submission_id}: {await writing.apply(session, e, model)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.essays")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pending")
    p.add_argument("--out", type=Path)
    a = sub.add_parser("apply")
    a.add_argument("file", type=Path)
    a.add_argument("--model", default="claude-code", help="who examined, stored with each run")
    args = parser.parse_args()
    asyncio.run(pending(args.out) if args.cmd == "pending" else apply(args.file, args.model))


if __name__ == "__main__":
    main()
