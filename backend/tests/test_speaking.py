"""Speaking: fluency numbers, content checks, the recorded interview, transcription and examiner runs."""

import pytest

from app.models.enums import TestKind as Kind
from app.services import scoring, speaking
from scripts.content.checks import check_speaking_section
from scripts.content.schema import CSection
from scripts.content.seed import seed_test
from tests.content_fixture import make
from tests.test_attempts import T0, clock  # noqa: F401  (fixture)
from tests.test_auth import login

C = speaking.CRITERIA
OPUS = b"\x1aE\xdf\xa3 fake webm bytes"
SPOKEN = "Well I usually cook at home because it is cheaper"


def words(text: str, start: float = 0.5, gap: float = 0.3, p: float = 0.9) -> list[dict]:
    out, t = [], start
    for w in text.split():
        out.append({"w": w, "start": round(t, 2), "end": round(t + 0.25, 2), "p": p})
        t += 0.25 + gap
    return out


def fake_transcribe(audio: bytes) -> dict:
    return {"text": SPOKEN, "words": words(SPOKEN)}


def test_stats_and_annotated_transcript():
    w = words("um I think") + words("it was er good", start=6.0, p=0.3)
    t = {"text": "", "words": w}
    s = speaking.stats([(t, 30_000)])
    assert (s["words"], s["fillers"], s["long_pauses"], s["wpm"]) == (5, 2, 1, 10)  # "um" and "er" aren't words
    assert s["unsure_words"] == ["it", "was", "good"]
    assert speaking.annotated(t) == "um I think [pause 4.2s] it was er good"
    assert speaking.stats([]) == {"words": 0, "wpm": 0, "fillers": 0, "long_pauses": 0, "unsure_words": []}


def lines(part: int) -> list[dict]:
    """Examiner lines: an intro (no answer), then questions; Part 2 starts with the long turn."""
    n, answer_s = {1: (9, 30), 2: (2, 30), 3: (5, 60)}[part]
    asks = [{"speaker": "examiner", "text": f"Part {part} question {i}?", "answer_s": answer_s} for i in range(n)]
    if part == 2:
        asks[0] = {"speaker": "examiner", "text": "Can you start speaking now, please?", "answer_s": 120}
    return [{"speaker": "examiner", "text": f"Now, Part {part}."}] + asks


def speaking_section() -> dict:
    parts = []
    for n in (1, 2, 3):
        ls = lines(n)
        parts.append({
            "number": n, "context": "speaking_interview", "topic": "food-cooking",
            "script": {"speakers": [{"id": "examiner", "role": "Examiner", "accent": "en-GB", "gender": "female"}], "lines": ls},
            "cue_card": {"task": "Describe a meal you enjoyed.", "bullets": ["where it was", "who you were with", "what you ate"],
                         "final": "and explain why you enjoyed it."} if n == 2 else None,
            "audio": {"url": f"/media/audio/fixture-s{n}.mp3", "duration_ms": 2000 * len(ls), "tts_provider": "fake",
                      "voices": {"examiner": "bf_x"},
                      "segments": [{"speaker": "examiner", "accent": "en-GB", "start_ms": 2000 * i, "end_ms": 2000 * i + 1500,
                                    "text": ln["text"], "answer_s": ln.get("answer_s")} for i, ln in enumerate(ls)]},
        })
    return {"skill": "speaking", "duration_s": 1200, "parts": parts}


def test_speaking_content_checks():
    good = CSection.model_validate(speaking_section())
    assert check_speaking_section(good) == []
    bad = CSection.model_validate(speaking_section())
    bad.parts[1].cue_card = None
    bad.parts[0].script.lines = bad.parts[0].script.lines[:3]
    errors = check_speaking_section(bad)
    assert any("cue card" in e for e in errors) and any("S1 2 questions" in e for e in errors)


def verdict(asec_id: int, *b: int) -> speaking.Evaluation:
    return speaking.Evaluation.model_validate({
        "attempt_section_id": asec_id, "off_topic_flags": [],
        "criteria": {c: {"band": band, "justification": "j", "evidence": ["cook at home"]} for c, band in zip(C, b)},
        "errors": [{"category": "word_choice", "original": "it is cheaper", "correction": "it's cheaper", "explanation": "-"}],
        "weakness_tags": ["short_answers"], "to_reach_next_half_band": ["extend answers"], "improved_paragraph_example": "…",
    })


@pytest.fixture
async def speaking_mock(db):
    t = make()
    t.slug, t.kind, t.sections[0].duration_s = "fixture-speaking", Kind.mock, 3600
    t.sections.append(CSection.model_validate(speaking_section()))
    async with db() as s:
        await seed_test(s, t)


async def test_full_mock_with_speaking_records_transcribes_and_scores(client, user, speaking_mock, clock, db):
    await login(client)
    test_id = (await client.get("/api/tests")).json()[0]["id"]
    a = (await client.post("/api/attempts", json={"mode": "full_mock", "test_id": test_id})).json()
    assert [s["skill"] for s in a["sections"]] == ["reading", "speaking"]  # Speaking comes last
    reading, ssec = (f"/api/attempts/{a['id']}/sections/{s['id']}" for s in a["sections"])
    await client.post(f"{reading}/start")
    await client.post(f"{reading}/submit")

    sec = (await client.post(f"{ssec}/start")).json()["sections"][1]
    assert sec["deadline_at"].startswith("2026-10-15T09:20")  # 20-minute safety net, never time-scaled
    p2 = sec["parts"][1]
    assert p2["cue_card"]["bullets"][0] == "where it was" and p2["transcript"][1]["answer_s"] == 120
    assert sec["parts"][0]["cue_card"] is None and sec["parts"][0]["transcript"][0]["answer_s"] is None

    put = lambda part, line, body=OPUS, mime="audio/webm;codecs=opus": client.put(  # noqa: E731
        f"{ssec}/speaking/{part}/{line}?duration_ms=999999", content=body, headers={"content-type": mime})
    assert (await put(1, 0)).status_code == 422  # the intro asks nothing
    assert (await put(1, 99)).status_code == 422
    assert (await put(1, 1, mime="text/plain")).status_code == 415
    assert (await put(1, 1, body=b"x" * (speaking.MAX_AUDIO_BYTES + 1))).status_code == 413
    for part, line in [(1, 1), (1, 1), (2, 1), (3, 1)]:  # (1, 1) twice: a retried upload replaces the first
        assert (await put(part, line)).status_code == 204
    again = (await client.get(f"/api/attempts/{a['id']}")).json()["sections"][1]
    assert [(r["part_number"], r["line_no"]) for r in again["recorded"]] == [(1, 1), (2, 1), (3, 1)]  # resume point

    done = (await client.post(f"{ssec}/submit")).json()
    assert done["status"] == "completed" and (await put(3, 2)).status_code == 409  # closed after submit
    report = (await client.get(f"/api/attempts/{a['id']}/report")).json()
    sp = report["report"]["sections"][1]
    assert sp["band"] is None and not sp["transcribed"] and report["overall_band"] is None
    answer = sp["parts"][1]["answers"][0]
    assert answer["duration_ms"] == 125_000  # the client's duration, capped at the answer time + 5 s
    audio = await client.get(f"/api/attempts/{a['id']}/speaking/{answer['id']}/audio")
    assert audio.content == OPUS and audio.headers["content-type"] == "audio/webm"

    async with db() as s:
        interviews = await speaking.pending(s, fake_transcribe)
    assert len(interviews) == 1 and interviews[0]["overall"]["words"] == 30
    assert interviews[0]["parts"][1]["cue_card"]["task"] == "Describe a meal you enjoyed."
    assert interviews[0]["parts"][1]["answers"][0]["max_s"] == 120
    asec_id = interviews[0]["attempt_section_id"]
    assert (await client.get(f"/api/attempts/{a['id']}/report")).json()["report"]["sections"][1]["transcribed"]

    async with db() as s:
        bad = verdict(asec_id, 6, 6, 6, 6)
        bad.criteria.grammar.evidence = ["words never said"]
        assert (await speaking.apply(s, bad, "claude-code")).startswith("rejected")
    async with db() as s:
        assert (await speaking.apply(s, verdict(asec_id, 6, 7, 6, 6), "claude-code")).startswith("run 1")
    async with db() as s:
        assert (await speaking.apply(s, verdict(asec_id, 7, 7, 6, 6), "claude-code")).startswith("scored")
        assert await speaking.pending(s, fake_transcribe) == []

    report = (await client.get(f"/api/attempts/{a['id']}/report")).json()
    r_band, s_band = (s["band"] for s in report["report"]["sections"])
    assert s_band == 6.5  # criteria 6, 7, 6, 6 → mean 6.25 → rounds up
    assert report["overall_band"] == scoring.overall_band([r_band, s_band]) and not report["overall_is_estimate"]


async def test_silent_speaking_test_scores_zero(client, user, speaking_mock, clock, db):
    await login(client)
    test_id = (await client.get("/api/tests")).json()[0]["id"]
    a = (await client.post("/api/attempts", json={"mode": "section_mock", "test_id": test_id, "skill": "speaking"})).json()
    url = f"/api/attempts/{a['id']}/sections/{a['sections'][0]['id']}"
    await client.post(f"{url}/start")
    await client.put(f"{url}/speaking/1/1?duration_ms=3000", content=OPUS, headers={"content-type": "audio/ogg"})
    await client.post(f"{url}/submit")
    async with db() as s:  # recorded, but nothing rateable was said
        assert await speaking.pending(s, lambda audio: {"text": "", "words": []}) == []
    report = (await client.get(f"/api/attempts/{a['id']}/report")).json()["report"]["sections"][0]
    assert report["band"] == 0 and report["result"]["criteria"]["fluency_coherence"]["band"] == 0
