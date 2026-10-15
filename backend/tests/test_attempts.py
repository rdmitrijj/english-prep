"""Reading section mock end to end: start, autosave, timer expiry, scoring and report."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.attempts import Response
from app.models.enums import TestKind as Kind

from app.services import timer
from scripts.content.seed import seed_test
from tests.content_fixture import make
from tests.test_auth import login

T0 = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
# Leaky field names: none of these may appear anywhere in an exam payload.
SECRET_FIELDS = {"accepted", "explanation", "evidence", "is_correct", "error_class", "difficulty", "sub_skill"}


@pytest.fixture
def clock(monkeypatch):
    """A frozen exam clock: set `clock.now` to move time."""
    class Clock:
        now = T0
    monkeypatch.setattr(timer, "now", lambda: Clock.now)
    return Clock


@pytest.fixture
async def mock_test(db):
    t = make()
    t.kind, t.sections[0].duration_s = Kind.mock, 3600
    async with db() as s:
        await seed_test(s, t)


async def start_exam(client):
    test_id = (await client.get("/api/tests")).json()[0]["id"]
    r = await client.post("/api/attempts", json={"mode": "section_mock", "test_id": test_id, "skill": "reading"})
    assert r.status_code == 201, r.text
    attempt = r.json()
    assert attempt["sections"][0]["parts"] is None  # nothing visible before the start
    sid = attempt["sections"][0]["id"]
    attempt = (await client.post(f"/api/attempts/{attempt['id']}/sections/{sid}/start")).json()
    questions = {q["number"]: q["id"] for p in attempt["sections"][0]["parts"] for g in p["groups"] for q in g["questions"]}
    return attempt["id"], sid, questions


def keys_of(obj) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | set().union(*map(keys_of, obj.values()))
    if isinstance(obj, list):
        return set().union(*map(keys_of, obj))
    return set()


async def test_exam_payload_never_contains_keys(client, user, mock_test, clock):
    await login(client)
    aid, sid, questions = await start_exam(client)
    payload = (await client.get(f"/api/attempts/{aid}")).json()
    assert not keys_of(payload) & SECRET_FIELDS
    assert len(questions) == 8
    assert payload["sections"][0]["deadline_at"] == (T0 + timedelta(hours=1)).isoformat().replace("+00:00", "Z")


async def test_autosave_restores_state_and_counts_changes(client, user, db, mock_test, clock):
    await login(client)
    aid, sid, q = await start_exam(client)
    url = f"/api/attempts/{aid}/sections/{sid}/responses"
    ui = {"highlights": [{"paragraph": "A", "start": 4, "end": 12}], "current": 4}
    assert (await client.put(url, json={"responses": [{"question_id": q[4], "answer": "summer", "time_ms": 4000}],
                                        "ui_state": ui})).status_code == 200
    await client.put(url, json={"responses": [{"question_id": q[4], "answer": "winter", "flagged": True,
                                                "time_ms": 3_600_000}]})  # absurd delta gets capped
    state = (await client.get(f"/api/attempts/{aid}")).json()["sections"][0]
    assert state["ui_state"] == ui
    assert state["responses"] == [{"question_id": q[4], "answer": "winter", "flagged": True}]
    async with db() as s:
        assert (await s.scalar(select(Response.change_count))) == 1

    report = (await client.post(f"/api/attempts/{aid}/sections/{sid}/submit")).json()
    assert report["status"] == "completed"
    q4 = next(x for x in (await client.get(f"/api/attempts/{aid}/report")).json()["report"]["sections"][0]["questions"]
              if x["number"] == 4)
    assert q4["time_ms"] == 4000 + 8000 and q4["is_correct"]


async def test_scoring_and_report(client, user, mock_test, clock):
    await login(client)
    aid, sid, q = await start_exam(client)
    answers = {1: "FALSE", 2: "FALSE", 3: "TRUE", 4: "winters", 5: "nutrition", 6: "B", 7: "ii"}  # 8 left blank
    await client.put(f"/api/attempts/{aid}/sections/{sid}/responses",
                     json={"responses": [{"question_id": q[n], "answer": a} for n, a in answers.items()]})
    assert (await client.get(f"/api/attempts/{aid}/report")).status_code == 409  # not finished yet
    clock.now = T0 + timedelta(minutes=20)
    await client.post(f"/api/attempts/{aid}/sections/{sid}/submit")

    section = (await client.get(f"/api/attempts/{aid}/report")).json()["report"]["sections"][0]
    assert section["raw"] == 5 and section["total"] == 8
    assert section["band_is_estimate"]  # 5/40 is below the official table
    assert section["submit_reason"] == "user" and section["time_used_ms"] == 20 * 60 * 1000
    errors = {x["number"]: x["error_class"] for x in section["questions"]}
    assert errors == {1: None, 2: "tfng:NG→F", 3: None, 4: "plural_singular", 5: None, 6: None, 7: None, 8: "blank"}
    assert {"qtype": "tfng", "correct": 2, "total": 3} in section["by_type"]


async def test_timer_expiry_auto_submits_and_rejects_late_saves(client, user, mock_test, clock):
    await login(client)
    aid, sid, q = await start_exam(client)
    url = f"/api/attempts/{aid}/sections/{sid}/responses"
    await client.put(url, json={"responses": [{"question_id": q[1], "answer": "FALSE"}]})

    clock.now = T0 + timedelta(hours=1, seconds=5)  # past the deadline but inside the network grace
    assert (await client.put(url, json={"responses": [{"question_id": q[3], "answer": "TRUE"}]})).status_code == 200

    clock.now = T0 + timedelta(hours=1, seconds=11)
    assert (await client.put(url, json={"responses": [{"question_id": q[5], "answer": "nutrition"}]})).status_code == 409
    attempt = (await client.get(f"/api/attempts/{aid}")).json()
    assert attempt["status"] == "completed"
    assert attempt["sections"][0]["submit_reason"] == "timeout"
    assert (await client.get(f"/api/attempts/{aid}/report")).json()["report"]["sections"][0]["raw"] == 2


async def test_attempts_are_private_and_practice_tests_are_not_mocks(client, user, db, clock):
    async with db() as s:
        await seed_test(s, make())  # kind = practice
    await login(client)
    assert (await client.get("/api/tests")).json() == []
    r = await client.post("/api/attempts", json={"mode": "section_mock", "test_id": 1, "skill": "reading"})
    assert r.status_code == 404
    assert (await client.get("/api/attempts/999")).status_code == 404
