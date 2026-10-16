"""Render Listening audio (PLAN §6.6). Each script line is synthesised with its speaker's voice, the PCM chunks are
joined with exact silences, and the result is encoded to MP3 once. Because every chunk's length is known, the
transcript timestamps are exact and free.

    python -m scripts.content.audio render mock-01                     # TTS_PROVIDER from .env
    python -m scripts.content.audio render mock-01 --provider fake     # free tones, for trying the app
    uv run --with kokoro-onnx python -m scripts.content.audio render mock-01 --provider kokoro   # free local voices

Synthesised lines are cached in content/.tts-cache/, so re-rendering after an edit only pays for changed lines.
"""

import argparse
import hashlib
import random
import subprocess
import tempfile
import wave
from pathlib import Path

from app.config import get_settings
from scripts.content.generate import finalize, save
from scripts.content.offline import load
from scripts.content.schema import CAudio, CPart, Segment, Speaker
from scripts.content.spec import LINE_GAP_S
from scripts.content.tts import PROVIDERS, SAMPLE_RATE, synthesize, voice_pool

FALLBACK = {"en-NZ": ["en-AU", "en-GB"], "en-CA": ["en-US"], "en-AU": ["en-GB"], "en-US": ["en-CA"], "en-GB": []}


def ms(pcm_bytes: int) -> int:
    return pcm_bytes // 2 * 1000 // SAMPLE_RATE  # 16-bit samples


def silence(seconds: float) -> bytes:
    return bytes(2 * round(seconds * SAMPLE_RATE))


def stitch(chunks: list[tuple[bytes, float]]) -> tuple[bytes, list[tuple[int, int]]]:
    """Join (pcm, pause_after_s) chunks; return the audio and each chunk's exact (start_ms, end_ms)."""
    pcm, spans = bytearray(), []
    for chunk, pause in chunks:
        start = ms(len(pcm))
        pcm += chunk
        spans.append((start, ms(len(pcm))))
        pcm += silence(pause)
    return bytes(pcm), spans


def assign_voices(speakers: list[Speaker], pool: dict, rng: random.Random, fixed: dict[str, str] | None = None) -> dict[str, str]:
    """A distinct voice per speaker, matching accent and gender (with a near accent as fallback).
    `fixed` pins voices, e.g. the same narrator throughout a test."""
    out = {sp.id: (fixed or {})[sp.id] for sp in speakers if sp.id in (fixed or {})}
    used = set(out.values())
    for sp in (sp for sp in speakers if sp.id not in out):
        for accent in [sp.accent, *FALLBACK[sp.accent]]:
            choices = [v for v in pool.get(accent, {}).get(sp.gender, []) if v not in used]
            if choices:
                out[sp.id] = rng.choice(choices)
                used.add(out[sp.id])
                break
        else:
            raise RuntimeError(f"no unused {sp.gender} voice for {sp.accent} (speaker {sp.id})")
    return out


def cached_synthesize(text: str, voice: str, provider: str) -> bytes:
    s = get_settings()
    model = s.elevenlabs_model if provider == "elevenlabs" else ""
    path = Path(s.content_dir) / ".tts-cache" / (hashlib.sha256(f"{provider}|{model}|{voice}|{text}".encode()).hexdigest() + ".pcm")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(synthesize(text, voice, provider))
    return path.read_bytes()


def encode_mp3(pcm: bytes, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(pcm)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name, "-ac", "1", "-b:a", "64k", str(out)], check=True)


def render_part(part: CPart, name: str, provider: str, fixed: dict[str, str] | None = None) -> CAudio:
    voices = assign_voices(part.script.speakers, voice_pool(provider), random.Random(name), fixed)
    accents = {sp.id: sp.accent for sp in part.script.speakers}
    lines = part.script.lines
    chunks = [(cached_synthesize(ln.text, voices[ln.speaker], provider), LINE_GAP_S + ln.pause_after_s) for ln in lines]
    pcm, spans = stitch(chunks)
    encode_mp3(pcm, Path(get_settings().content_dir) / "media" / "audio" / f"{name}.mp3")
    return CAudio(
        url=f"/media/audio/{name}.mp3", duration_ms=ms(len(pcm)), tts_provider=provider, voices=voices,
        segments=[Segment(speaker=ln.speaker, accent=accents[ln.speaker], start_ms=a, end_ms=b, text=ln.text)
                  for ln, (a, b) in zip(lines, spans)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.content.audio")
    parser.add_argument("cmd", choices=["render"])
    parser.add_argument("slug")
    parser.add_argument("--provider", choices=list(PROVIDERS))
    args = parser.parse_args()
    provider = args.provider or get_settings().tts_provider
    test = load(args.slug)
    parts = [p for s in test.sections for p in s.parts if p.script]
    # One narrator for the whole test, as in the real recordings.
    narrator = next(sp for sp in parts[0].script.speakers if sp.id == "narrator")
    fixed = assign_voices([narrator], voice_pool(provider), random.Random(args.slug))
    for part in parts:
        part.audio = render_part(part, f"{args.slug}-p{part.number}", provider, fixed)
        print(f"L{part.number}: {part.audio.duration_ms / 60000:.1f} min, voices {part.audio.voices}")
    save(finalize(test))
    total = sum(p.audio.duration_ms for s in test.sections for p in s.parts if p.audio) / 60000
    print(f"{test.status.value}: {args.slug}  ({total:.1f} min of audio, {len(test.check_errors)} check errors)")
    for e in test.check_errors:
        print("  check:", e)


if __name__ == "__main__":
    main()
