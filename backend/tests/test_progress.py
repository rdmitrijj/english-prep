"""M7: the weakness formula on hand-computed cases, Leitner transitions, the trainer mix, and the review loop end to end."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.attempts import ReviewItem
from app.routers.trainer import compose
from app.services.srs import next_state
from app.services.weakness import Answer, goal_for, tag_score, weight
from scripts.content.seed import seed_test
from tests.content_fixture import make
from tests.test_attempts import T0, clock  # noqa: F401  (fixture)
from tests.test_auth import login

DAY = timedelta(days=1)


def answers(correct: int, wrong: int, age: float = 0, time_ms: int = 0) -> list[Answer]:
    return [Answer(True, age, time_ms)] * correct + [Answer(False, age, time_ms)] * wrong


def test_recent_answers_count_more():
    assert (weight(0), weight(14), weight(28)) == (1, 0.5, 0.25)
    old_misses = tag_score(answers(4, 0) + answers(0, 4, age=28), mu=0.5, goal=0.75, target_ms=None)
    # 4 right today (weight 4) beat 4 wrong a month ago (weight 1): p = (4 + 3) / (5 + 6)
    assert old_misses["accuracy"] == pytest.approx(7 / 11)


def test_few_answers_are_pulled_toward_the_section_accuracy():
    two_right = tag_score(answers(2, 0), mu=0.5, goal=0.75, target_ms=None)
    assert two_right["accuracy"] == pytest.approx(5 / 8)  # (2 + 6·0.5) / (2 + 6), not 100%
    assert not two_right["weak"]


def test_weakness_needs_eight_answers_and_a_gap_to_the_goal():
    s = tag_score(answers(6, 4), mu=0.6, goal=0.75, target_ms=None)
    assert s["accuracy"] == pytest.approx(0.6) and s["score"] == pytest.approx(0.15) and s["weak"]  # (6 + 3.6) / 16
    assert not tag_score(answers(0, 7), mu=0.6, goal=0.75, target_ms=None)["weak"]  # 7 misses: too few to judge
    assert not tag_score(answers(14, 2), mu=0.8, goal=0.75, target_ms=None)["weak"]


def test_pace_penalty_grows_then_caps():
    on_pace = tag_score(answers(8, 0, time_ms=60_000), mu=1, goal=1, target_ms=90_000)
    a_bit_slow = tag_score(answers(8, 0, time_ms=108_000), mu=1, goal=1, target_ms=90_000)  # r = 1.2
    very_slow = tag_score(answers(8, 0, time_ms=270_000), mu=1, goal=1, target_ms=90_000)  # r = 3
    assert on_pace["score"] == pytest.approx(0)
    assert a_bit_slow["score"] == pytest.approx(0.06) and a_bit_slow["weak"]  # accurate but slow is still a weakness
    assert very_slow["score"] == pytest.approx(0.15)


def test_goal_comes_from_the_band_table():
    rows = [{"min_raw": 23, "max_raw": 26, "band": 6.0}, {"min_raw": 27, "max_raw": 29, "band": 6.5},
            {"min_raw": 30, "max_raw": 31, "band": 7.0}, {"min_raw": 32, "max_raw": 34, "band": 7.5}]
    assert goal_for(rows, 7.0) == 0.75 and goal_for(rows, 6.5) == 27 / 40


def test_leitner_transitions():
    now = T0
    assert next_state(None, None, False, now) == (1, now + DAY)  # a miss anywhere: box 1, due tomorrow
    assert next_state(None, None, True, now) is None  # a right answer on an unqueued question queues nothing
    assert next_state(1, now + DAY, True, now) == (1, now + DAY)  # not due yet: nothing moves
    assert next_state(1, now, True, now) == (2, now + 3 * DAY)
    assert next_state(4, now, True, now) == (5, now + 35 * DAY)
    assert next_state(5, now, True, now) is None  # retired
    assert next_state(4, now, False, now) == (1, now + DAY)


def test_trainer_mix_is_about_40_40_20():
    due = [(1, 4), (2, 4), (3, 4)]
    weak = [(10, 4), (11, 4), (12, 4)]
    slow = [(20, 4), (21, 4)]
    fill = [(30, 4), (31, 4), (32, 4)]
    assert compose(due, weak, slow, fill) == [1, 2, 10, 11, 20]  # 8 due + 8 weak + 4 slow = 20
    assert compose([], weak, slow, fill) == [10, 11, 20, 12, 30]  # no reviews due: weak tags, then anything new
    assert compose(due, [], [], []) == [1, 2]  # never the same group twice, never padding


@pytest.fixture
async def practice(db):
    async with db() as s:
        await seed_test(s, make())


async def test_a_miss_comes_back_tomorrow_in_the_trainer(client, user, practice, clock, db):
    await login(client)
    session = (await client.post("/api/practice/sessions", json={"skill": "reading", "qtype": "tfng"})).json()
    sec = session["sections"][0]
    group = sec["parts"][0]["groups"][0]
    q1, q2, q3 = (q["id"] for q in group["questions"])
    url = f"/api/attempts/{session['id']}/sections/{sec['id']}"
    await client.put(f"{url}/responses", json={"responses": [
        {"question_id": q1, "answer": "TRUE"}, {"question_id": q2, "answer": "NOT GIVEN"}, {"question_id": q3, "answer": "TRUE"}]})
    await client.post(f"/api/practice/sessions/{session['id']}/check-group", json={"group_id": group["id"]})
    await client.post(f"{url}/submit")  # finishing re-marks the checked group: the queue must not count it twice

    async with db() as s:
        items = list(await s.scalars(select(ReviewItem)))
    assert [(i.question_id, i.box, i.due_at) for i in items] == [(q1, 1, T0 + DAY)]  # only the miss is queued
    dash = (await client.get("/api/dashboard")).json()
    assert dash["reviews_due"] == 0 and dash["skills"]["reading"]["answers"] == 3

    clock.now = T0 + DAY
    assert (await client.get("/api/dashboard")).json()["reviews_due"] == 1
    trainer = (await client.post("/api/trainer/sessions", json={"skill": "reading"})).json()
    assert trainer["mode"] == "trainer"
    tsec = trainer["sections"][0]
    assert tsec["parts"][0]["groups"][0]["id"] == group["id"]  # the due review comes first
    turl = f"/api/attempts/{trainer['id']}/sections/{tsec['id']}"
    await client.put(f"{turl}/responses", json={"responses": [{"question_id": q1, "answer": "FALSE"}]})
    r = await client.post(f"/api/practice/sessions/{trainer['id']}/check-group", json={"group_id": group["id"]})
    assert r.status_code == 200
    async with db() as s:
        item = await s.scalar(select(ReviewItem).where(ReviewItem.question_id == q1))
    assert (item.box, item.due_at) == (2, T0 + 4 * DAY)  # right on its due day: next box, 3 days on
