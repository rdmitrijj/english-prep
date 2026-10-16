"""TTS seam (PLAN §6.6): `synthesize(text, voice_id)` → 24 kHz mono 16-bit PCM.
Swapping vendor = one function in PROVIDERS + one block in voices.json.

    python -m scripts.content.tts voices            # list your ElevenLabs voices with their labels
    python -m scripts.content.tts voices --write    # pick voices by accent/gender into voices.json

TTS_PROVIDER=kokoro is free and local (Kokoro-82M, Apache-2.0): it needs `uv run --with kokoro-onnx` and the model
files in KOKORO_DIR (kokoro-v1.0.onnx + voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases).
"""

import argparse
import json
import math
import urllib.parse
import urllib.request
import zlib
from array import array
from functools import cache
from pathlib import Path

from app.config import get_settings
from app.services.normalize import count_words
from scripts.content.spec import SPEECH_WPS

SAMPLE_RATE = 24_000
VOICES_FILE = Path(__file__).with_name("voices.json")
ELEVEN = "https://api.elevenlabs.io"


class TTSError(RuntimeError):
    pass


def _eleven_request(method: str, path: str, query: dict | None = None, body: dict | None = None) -> bytes:
    key = get_settings().elevenlabs_api_key
    if not key:
        raise TTSError("ELEVENLABS_API_KEY is not set: add it to .env (or use TTS_PROVIDER=fake for silent test audio)")
    url = f"{ELEVEN}{path}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
    req = urllib.request.Request(url, method=method, headers={"xi-api-key": key, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise TTSError(f"ElevenLabs {e.code}: {e.read()[:300]!r}") from e


def _elevenlabs(text: str, voice_id: str) -> bytes:
    return _eleven_request("POST", f"/v1/text-to-speech/{voice_id}", {"output_format": "pcm_24000"},
                           {"text": text, "model_id": get_settings().elevenlabs_model})


def _fake(text: str, voice_id: str) -> bytes:
    """Free stand-in for development: a quiet tone as long as the line would take to say, pitched per voice."""
    freq = 160 + zlib.crc32(voice_id.encode()) % 240  # whole Hz → one second of tone repeats seamlessly
    second = array("h", (int(2000 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)) for i in range(SAMPLE_RATE)))
    n = int(max(0.6, count_words(text) / SPEECH_WPS) * SAMPLE_RATE)
    return (second.tobytes() * (n // SAMPLE_RATE + 1))[: n * 2]


@cache
def _kokoro_model():
    from kokoro_onnx import Kokoro  # optional: only the local render needs it

    d = Path(get_settings().kokoro_dir).expanduser()
    return Kokoro(str(d / "kokoro-v1.0.onnx"), str(d / "voices-v1.0.bin"))


def _kokoro(text: str, voice_id: str) -> bytes:
    import numpy as np  # comes with kokoro-onnx

    samples, rate = _kokoro_model().create(text, voice=voice_id, lang="en-gb" if voice_id[0] == "b" else "en-us")
    assert rate == SAMPLE_RATE
    return (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()


PROVIDERS = {"elevenlabs": _elevenlabs, "fake": _fake, "kokoro": _kokoro}
# Kokoro has British and American voices only; the other accents fall back to these (audio.FALLBACK).
KOKORO_VOICES = {
    "en-GB": {"female": ["bf_emma", "bf_isabella", "bf_alice"], "male": ["bm_george", "bm_fable", "bm_lewis", "bm_daniel"]},
    "en-US": {"female": ["af_heart", "af_bella", "af_nicole", "af_sarah"], "male": ["am_michael", "am_fenrir", "am_puck"]},
}


def synthesize(text: str, voice_id: str, provider: str | None = None) -> bytes:
    return PROVIDERS[provider or get_settings().tts_provider](text, voice_id)


def voice_pool(provider: str) -> dict[str, dict[str, list[str]]]:
    """accent → gender → voice ids."""
    if provider == "fake":
        return {a: {g: [f"fake-{a}-{g}-{i}" for i in range(3)] for g in ("female", "male")}
                for a in ("en-GB", "en-AU", "en-NZ", "en-US", "en-CA")}
    if provider == "kokoro":
        return KOKORO_VOICES
    pools = json.loads(VOICES_FILE.read_text()) if VOICES_FILE.exists() else {}
    if provider not in pools:
        raise TTSError(f"no {provider} voices in {VOICES_FILE.name}: run python -m scripts.content.tts voices --write")
    return pools[provider]


ACCENT_LABELS = {"british": "en-GB", "english": "en-GB", "australian": "en-AU", "new zealand": "en-NZ",
                 "kiwi": "en-NZ", "american": "en-US", "canadian": "en-CA"}


def list_eleven_voices() -> list[dict]:
    voices, token = [], None
    while True:
        query = {"page_size": 100} | ({"next_page_token": token} if token else {})
        page = json.loads(_eleven_request("GET", "/v2/voices", query))
        voices += page["voices"]
        if not page.get("has_more"):
            return voices
        token = page["next_page_token"]


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.content.tts")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("voices")
    v.add_argument("--write", action="store_true", help="save voices grouped by accent and gender into voices.json")
    args = parser.parse_args()

    pool: dict[str, dict[str, list[str]]] = {}
    for voice in list_eleven_voices():
        labels = {k: str(val).lower() for k, val in (voice.get("labels") or {}).items()}
        accent = ACCENT_LABELS.get(labels.get("accent", ""))
        print(f"{voice['voice_id']}  {voice.get('name', '?'):<24} {labels}  →  {accent or '-'}")
        if accent and labels.get("gender") in ("female", "male"):
            pool.setdefault(accent, {}).setdefault(labels["gender"], []).append(voice["voice_id"])
    if args.write:
        pools = json.loads(VOICES_FILE.read_text()) if VOICES_FILE.exists() else {}
        pools["elevenlabs"] = pool
        VOICES_FILE.write_text(json.dumps(pools, indent=2) + "\n")
        print(f"wrote {VOICES_FILE.name}: " + ", ".join(f"{a}: {sum(map(len, g.values()))}" for a, g in sorted(pool.items())))


if __name__ == "__main__":
    main()
