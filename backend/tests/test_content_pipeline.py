"""Seed, verify-compare and the LLM seam — all without calling a paid API."""

from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.models.attempts import Attempt, AttemptSection, Response
from app.models.content import AnswerKey, Question, Tag, Test
from app.models.enums import ContentStatus
from app.models.usage import AiUsage
from app.services import llm, usage
from scripts.content.schema import PassageDraft, VerifierAnswer
from scripts.content.seed import seed_test
from scripts.content.verify import candidate_view, compare
from tests.content_fixture import make


async def count(session, model):
    return await session.scalar(select(func.count()).select_from(model))


async def test_seed_is_idempotent_and_replaces_changed_content(db):
    async with db() as s:
        assert await seed_test(s, make()) == "created"
    async with db() as s:
        assert await seed_test(s, make()) == "unchanged"
        assert (await count(s, Test), await count(s, Question), await count(s, AnswerKey), await count(s, Tag)) == (1, 8, 8, 1)

    changed = make()
    changed.title = "Keeping bees, revised"
    async with db() as s:
        assert await seed_test(s, changed) == "replaced"
        assert await count(s, Test) == 1
        assert await count(s, Question) == 8
        key = await s.scalar(select(AnswerKey).join(Question).where(Question.number == 4))
        assert key.accepted == ["winter"]


async def test_seed_skips_unpublished_and_answered_tests(db, user):
    draft = make()
    draft.status = ContentStatus.needs_review
    async with db() as s:
        assert (await seed_test(s, draft)).startswith("skipped")
        assert await seed_test(s, make()) == "created"
        q = await s.scalar(select(Question).limit(1))
        attempt = Attempt(user_id=user.id, mode="practice")
        s.add(attempt)
        await s.flush()
        sec = AttemptSection(attempt_id=attempt.id, skill="reading")
        s.add(sec)
        await s.flush()
        s.add(Response(attempt_section_id=sec.id, question_id=q.id, answer="x"))
        await s.commit()
    changed = make()
    changed.title = "changed"
    async with db() as s:
        assert "already has answers" in await seed_test(s, changed)


def test_verifier_comparison():
    part = make().sections[0].parts[0]
    tfng, notes, mcq = part.groups[0], part.groups[1], part.groups[2]
    va = lambda answer, conf=0.95: VerifierAnswer(number=0, answer=answer, confidence=conf, note="")
    assert compare(tfng, tfng.questions[0], va(["false"])) is None  # case-insensitive labels
    assert compare(notes, notes.questions[0], va(["Winter."])) is None  # normalised text
    assert compare(mcq, mcq.questions[0], va(["C"])).reason == "verifier disagreed"
    assert compare(mcq, mcq.questions[0], va(["B"], conf=0.4)).reason.startswith("verifier unsure")
    assert compare(mcq, mcq.questions[0], None).reason == "verifier gave no answer"


def test_candidate_view_hides_answers():
    view = candidate_view(make().sections[0].parts[0])
    assert "Paragraph A" in view and "{4}" in view
    assert "NOT GIVEN" not in view  # an answer, not part of the shown rubric fixture
    assert "Paraphrase of the evidence" not in view and "nutrition\"" not in view


def test_token_cost():
    # 1M fresh input at $2 + 1M output at $10
    assert usage.token_cost("gpt-6.1-sol", 1_000_000, 0, 0, 1_000_000) == pytest.approx(12.0)
    with pytest.raises(ValueError):
        usage.token_cost("unknown-model", 1, 0, 0, 1)


async def test_structured_logs_usage_with_mocked_client(db, monkeypatch):
    parsed = PassageDraft(title="t", paragraphs=[], glossary=[])
    fake_response = SimpleNamespace(
        output_parsed=parsed, status="completed",
        usage=SimpleNamespace(input_tokens=1000, output_tokens=500,
                              input_tokens_details=SimpleNamespace(cached_tokens=200, cache_write_tokens=0)),
    )
    calls = []

    async def fake_parse(**kwargs):
        calls.append(kwargs)
        return fake_response

    monkeypatch.setattr(llm, "_client", lambda: SimpleNamespace(responses=SimpleNamespace(parse=fake_parse)))
    monkeypatch.setattr(usage, "SessionLocal", db)

    result = await llm.structured(purpose="test", model="gpt-6.1-sol", system="sys", user="hello",
                                  schema=PassageDraft, effort="low")
    assert result is parsed
    assert calls[0]["text_format"] is PassageDraft and calls[0]["reasoning"] == {"effort": "low"}
    assert calls[0]["input"] == [{"role": "user", "content": "hello"}]  # user text stays a separate message
    async with db() as s:
        row = await s.scalar(select(AiUsage))
        assert (row.purpose, row.input_tokens, row.cached_tokens, row.output_tokens) == ("test", 1000, 200, 500)
        assert row.cost_usd == pytest.approx((800 * 2 + 200 * 0.10 + 500 * 10) / 1_000_000)


def test_missing_api_key_is_a_clear_error(monkeypatch):
    llm._client.cache_clear()
    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(openai_api_key=None))
    with pytest.raises(llm.LLMError, match="OPENAI_API_KEY"):
        llm._client()
    llm._client.cache_clear()
