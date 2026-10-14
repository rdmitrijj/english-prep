"""The only module that talks to the LLM provider. Swap provider = reimplement `structured`.

Uses the OpenAI Responses API with Structured Outputs: the reply is guaranteed to match the Pydantic schema.
Reasoning models take `reasoning.effort` instead of `temperature`.
"""

from functools import lru_cache
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.services import usage

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class LLMError(RuntimeError):
    pass


@lru_cache
def _client() -> AsyncOpenAI:
    key = get_settings().openai_api_key
    if not key:
        raise LLMError("OPENAI_API_KEY is not set (put it in .env)")
    return AsyncOpenAI(api_key=key, max_retries=3, timeout=600)


async def structured[T: BaseModel](
    *, purpose: str, model: str, system: str, user: str, schema: type[T],
    effort: Effort = "medium", user_id: int | None = None,
) -> T:
    """System prompt + one user message → a validated `schema` instance. Logs cost to ai_usage."""
    resp = await _client().responses.parse(
        model=model,
        instructions=system,
        input=[{"role": "user", "content": user}],
        text_format=schema,
        reasoning={"effort": effort},
        store=False,
    )
    u = resp.usage
    cached = u.input_tokens_details.cached_tokens or 0
    cache_write = getattr(u.input_tokens_details, "cache_write_tokens", 0) or 0
    await usage.record(
        purpose=purpose, model=model, user_id=user_id,
        input_tokens=u.input_tokens, cached_tokens=cached, output_tokens=u.output_tokens,
        cost_usd=usage.token_cost(model, u.input_tokens, cached, cache_write, u.output_tokens),
    )
    if resp.output_parsed is None:
        raise LLMError(f"{purpose}: model returned no parsable output (status={resp.status})")
    return resp.output_parsed
