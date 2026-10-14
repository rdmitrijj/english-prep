"""Cost bookkeeping for every paid API call (PLAN §6.5). guard_ai() (rate limit + monthly cap) arrives in M6."""

from app.db import SessionLocal
from app.models.usage import AiUsage

# USD per 1M tokens: (input, cached input, cache write, output). Source: developers.openai.com/api/docs/pricing (2026-10).
PRICES: dict[str, tuple[float, float, float, float]] = {
    "gpt-6.1-sol": (2.00, 0.10, 2.50, 10.00),
    "gpt-5.6-terra": (2.00, 0.20, 2.00, 12.00),
}


def token_cost(model: str, input_tokens: int, cached: int, cache_write: int, output_tokens: int) -> float:
    if model not in PRICES:
        raise ValueError(f"No price for model {model!r}; add it to PRICES so the cost cap stays honest")
    p_in, p_cached, p_write, p_out = PRICES[model]
    fresh = input_tokens - cached - cache_write
    return (fresh * p_in + cached * p_cached + cache_write * p_write + output_tokens * p_out) / 1_000_000


async def record(*, purpose: str, model: str, user_id: int | None, input_tokens: int = 0, cached_tokens: int = 0,
                 output_tokens: int = 0, audio_seconds: int = 0, cost_usd: float) -> None:
    async with SessionLocal() as session:
        session.add(AiUsage(purpose=purpose, model=model, user_id=user_id, input_tokens=input_tokens,
                            cached_tokens=cached_tokens, output_tokens=output_tokens,
                            audio_seconds=audio_seconds, cost_usd=cost_usd))
        await session.commit()
