"""Listening in the app: deadline from the audio, no transcript in a mock, transcript and evidence in practice."""

from datetime import timedelta

import pytest

from app.config import get_settings
from app.models.enums import TestKind as Kind
from scripts.content.offline import listening_rubrics
from scripts.content.schema import CSection
from scripts.content.seed import seed_test
from tests.content_fixture import make
from tests.listening_fixture import listening_part
from tests.test_attempts import T0, clock  # noqa: F401  (fixture)
from tests.test_auth import login


def with_listening(kind: Kind):
    t = make()
    t.slug, t.kind, t.sections[0].duration_s = f"fixture-{kind}", kind, 3600
    part = listening_part()
    listening_rubrics(part)
    t.sections.insert(0, CSection(skill="listening", duration_s=None, parts=[part]))
    return t


@pytest.fixture
async def listening(db):
    async with db() as s:
        await seed_test(s, with_listening(Kind.mock))
        await seed_test(s, with_listening(Kind.practice))


async def test_listening_deadline_is_audio_plus_review_and_ignores_time_scale(client, user, listening, clock, monkeypatch):
    monkeypatch.setattr(get_settings(), "exam_time_scale", 0.05)
    await login(client)
    test = (await client.get("/api/tests")).json()[0]
    assert {s["skill"]: s["duration_s"] for s in test["sections"]} == {"listening": 9 + 120, "reading": 180}
    a = (await client.post("/api/attempts", json={"mode": "section_mock", "test_id": test["id"], "skill": "listening"})).json()
    sec = (await client.post(f"/api/attempts/{a['id']}/sections/{a['sections'][0]['id']}/start")).json()["sections"][0]
    assert sec["deadline_at"] == (T0 + timedelta(seconds=129)).isoformat().replace("+00:00", "Z")
    part = sec["parts"][0]
    assert part["audio"] == {"url": "/media/audio/fixture-p1.mp3", "duration_ms": 9000}
    assert part["transcript"] is None  # a mock never sends what is said


async def test_practice_listening_has_transcript_and_line_evidence(client, user, listening, clock):
    await login(client)
    options = (await client.get("/api/practice/options", params={"skill": "listening"})).json()
    assert {o["qtype"] for o in options} == {"form_completion", "mcq"}
    session = (await client.post("/api/practice/sessions", json={"skill": "listening", "qtype": "form_completion"})).json()
    sec = session["sections"][0]
    part = sec["parts"][0]
    assert [s["speaker"] for s in part["transcript"]][:2] == ["narrator", "clerk"]
    q1 = part["groups"][0]["questions"][0]["id"]
    await client.put(f"/api/attempts/{session['id']}/sections/{sec['id']}/responses",
                     json={"responses": [{"question_id": q1, "answer": "hartley"}]})
    fb = (await client.post(f"/api/practice/sessions/{session['id']}/check-group",
                            json={"group_id": part["groups"][0]["id"]})).json()
    assert fb[0]["is_correct"] and fb[0]["evidence"] == {"paragraph": "2", "quote": "My surname is Hartley"}
