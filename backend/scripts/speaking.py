"""Score Speaking tests with local Whisper + Claude Code examiners (M10), like scripts.essays for Writing.

    python -m scripts.speaking pending --out /srv/content/drafts/speaking.json   # transcribe new answers, export
    python -m scripts.speaking apply /srv/content/drafts/speaking-a.json          # store one examiner's verdicts

The workflow (when the user says "score my speaking"):
1. `pending` transcribes every answer not yet transcribed (faster-whisper, on this machine, free; the model is
   downloaded once into content/.whisper-cache/) and exports each submitted interview still needing a run.
2. Two blind examiner agents each read scripts/speaking_examiner.md + the export and write {"evaluations": [...]}.
3. `apply` each file; a pair that differs by more than one band on a criterion shows up in `pending` again for a
   third run. When an interview is complete, its band and the attempt report are updated.
Against production, run the same commands with DATABASE_URL pointing at Neon.
"""

import argparse
import asyncio
import json
import subprocess
from functools import cache
from pathlib import Path

from pydantic import BaseModel

from app.config import get_settings
from app.db import SessionLocal
from app.services import speaking

# Whisper tidies speech into fluent prose unless its prompt shows disfluencies; the examiners need the "um"s.
DISFLUENT_PROMPT = "Umm, let me think, like, hmm... Okay, so, uh, I- I think it's, er, quite good, you know."


@cache
def model():
    from faster_whisper import WhisperModel  # dev-only dependency: never imported by the app

    return WhisperModel(get_settings().whisper_model, device="cpu", compute_type="int8",
                        download_root=str(Path(get_settings().content_dir) / ".whisper-cache"))


def decode(audio: bytes):
    """Any browser recording (WebM, Ogg, MP4) → 16 kHz mono float samples, via the dev image's ffmpeg."""
    import numpy as np

    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
                         input=audio, capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def transcribe(audio: bytes) -> dict:
    segments, _ = model().transcribe(decode(audio), language="en", word_timestamps=True,
                                     condition_on_previous_text=False, initial_prompt=DISFLUENT_PROMPT)
    words = [{"w": w.word.strip(), "start": round(float(w.start), 2), "end": round(float(w.end), 2), "p": round(float(w.probability), 2)}
             for s in segments for w in s.words or []]
    return {"text": " ".join(w["w"] for w in words), "words": words}


class Batch(BaseModel):
    evaluations: list[speaking.Evaluation]


async def pending(out: Path | None) -> None:
    async with SessionLocal() as session:
        tests = await speaking.pending(session, transcribe)
    text = json.dumps({"interviews": tests}, indent=2, ensure_ascii=False)
    if out:
        out.write_text(text + "\n")
        print(f"{len(tests)} speaking tests need a run → {out}")
    else:
        print(text)


async def apply(path: Path, model_name: str) -> None:
    for e in Batch.model_validate_json(path.read_text()).evaluations:
        async with SessionLocal() as session:
            print(f"speaking test {e.attempt_section_id}: {await speaking.apply(session, e, model_name)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.speaking")
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
