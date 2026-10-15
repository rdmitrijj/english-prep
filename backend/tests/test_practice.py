"""Practice sessions: the pool, filters, check-group feedback and locking."""

import pytest

from app.models.enums import TestKind as Kind
from scripts.content.seed import seed_test
from tests.content_fixture import make
from tests.test_attempts import SECRET_FIELDS, keys_of
from tests.test_auth import login


@pytest.fixture
async def content(db):
    """The fixture passage twice: once as practice content, once as a mock (slug fixture-bees-mock)."""
    mock = make()
    mock.slug, mock.kind, mock.sections[0].duration_s = "fixture-bees-mock", Kind.mock, 3600
    async with db() as s:
        await seed_test(s, make())
        await seed_test(s, mock)


async def options(client):
    return (await client.get("/api/practice/options")).json()


async def test_mock_items_join_the_pool_only_after_that_mock_is_completed(client, user, content):
    await login(client)
    assert len(await options(client)) == 4  # the practice test's 4 groups only

    test_id = (await client.get("/api/tests")).json()[0]["id"]
    a = (await client.post("/api/attempts", json={"mode": "section_mock", "test_id": test_id, "skill": "reading"})).json()
    sid = a["sections"][0]["id"]
    await client.post(f"/api/attempts/{a['id']}/sections/{sid}/start")
    assert len(await options(client)) == 4  # started is not enough
    await client.post(f"/api/attempts/{a['id']}/sections/{sid}/submit")

    groups = await options(client)
    assert len(groups) == 8
    assert sum(g["seen"] for g in groups) == 4  # the completed mock's groups count as seen
    assert {g["level"] for g in groups} == {"easy"} and groups[0]["topic"] == "biology-ecology"


async def test_session_feedback_only_after_answering_and_answers_lock(client, user, content):
    await login(client)
    r = await client.post("/api/practice/sessions", json={"skill": "reading", "qtype": "tfng"})
    assert r.status_code == 201, r.text
    session = r.json()
    aid, sec = session["id"], session["sections"][0]
    assert sec["deadline_at"] is None and sec["started_at"]  # untimed but measured
    assert [g["qtype"] for p in sec["parts"] for g in p["groups"]] == ["tfng"]
    assert not keys_of(session) & SECRET_FIELDS and sec["feedback"] == []
    q = {q["number"]: q["id"] for q in sec["parts"][0]["groups"][0]["questions"]}
    gid = sec["parts"][0]["groups"][0]["id"]
    check = f"/api/practice/sessions/{aid}/check-group"
    save = f"/api/attempts/{aid}/sections/{sec['id']}/responses"

    assert (await client.post(check, json={"group_id": gid})).status_code == 409  # nothing answered yet

    await client.put(save, json={"responses": [{"question_id": q[1], "answer": "TRUE", "time_ms": 3000},
                                               {"question_id": q[2], "answer": "NOT GIVEN"}]})
    fb = {f["number"]: f for f in (await client.post(check, json={"group_id": gid})).json()}
    assert (fb[1]["is_correct"], fb[1]["error_class"], fb[1]["accepted"]) == (False, "tfng:F→T", ["FALSE"])
    assert fb[2]["is_correct"] and fb[3]["error_class"] == "blank"
    assert fb[1]["evidence"]["paragraph"] == "A" and fb[1]["explanation"]["correct"]

    assert (await client.put(save, json={"responses": [{"question_id": q[1], "answer": "FALSE"}]})).status_code == 409
    # time keeps counting on a checked question, as long as the answer is unchanged
    assert (await client.put(save, json={"responses": [{"question_id": q[1], "answer": "TRUE", "time_ms": 2000}]})).status_code == 200
    restored = (await client.get(f"/api/attempts/{aid}")).json()["sections"][0]
    assert len(restored["feedback"]) == 3  # feedback survives a refresh

    await client.post(f"/api/attempts/{aid}/sections/{sec['id']}/submit")
    report = (await client.get(f"/api/attempts/{aid}/report")).json()
    assert report["test_title"] == "Practice"
    s = report["report"]["sections"][0]
    assert (s["raw"], s["total"], s["band"]) == (1, 3, None)
    assert s["time_on_questions_ms"] == 5000


async def test_filters_and_unknown_groups(client, user, content):
    await login(client)
    r = await client.post("/api/practice/sessions", json={"skill": "reading", "qtype": "tfng", "level": "hard"})
    assert r.status_code == 404
    session = (await client.post("/api/practice/sessions", json={"skill": "reading", "topic": "biology-ecology"})).json()
    picked = [g["qtype"] for p in session["sections"][0]["parts"] for g in p["groups"]]
    assert sum(len(g["questions"]) for p in session["sections"][0]["parts"] for g in p["groups"]) == 8
    assert picked == ["tfng", "note_completion", "mcq", "matching_headings"]  # passage order, not pick order
    r = await client.post(f"/api/practice/sessions/{session['id']}/check-group", json={"group_id": 9999})
    assert r.status_code == 404
