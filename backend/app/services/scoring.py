"""Band arithmetic. Conversion tables live in the `band_tables` DB rows, never in this code."""

import math
from collections.abc import Iterable
from typing import Any


def band_for_raw(rows: list[dict[str, Any]], raw: int) -> tuple[float, bool]:
    """Look up a raw score (0–40) in a band table. Returns (band, is_estimate)."""
    for row in rows:
        if row["min_raw"] <= raw <= row["max_raw"]:
            return float(row["band"]), bool(row.get("estimated", False))
    raise ValueError(f"raw score {raw} not covered by band table")


def round_half_up(value: float) -> float:
    """Round to the nearest 0.5, with .25 → up and .75 → up (official IELTS rule, RESEARCH §5)."""
    return math.floor(value * 2 + 0.5) / 2


def overall_band(section_bands: Iterable[float]) -> float:
    bands = list(section_bands)
    return round_half_up(sum(bands) / len(bands))
