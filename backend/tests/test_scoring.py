import pytest
from sqlalchemy import select

from app.models.content import BandTable
from app.services.scoring import band_for_raw, overall_band


@pytest.mark.parametrize(
    "bands, expected",
    [
        ([6.5, 6.5, 5.0, 7.0], 6.5),  # avg 6.25 → 6.5   (official example A)
        ([4.0, 3.5, 4.0, 4.0], 4.0),  # avg 3.875 → 4.0  (official example B)
        ([6.5, 6.5, 5.5, 6.0], 6.0),  # avg 6.125 → 6.0  (official example C)
        ([7.0, 7.0, 7.0, 6.0], 7.0),  # avg 6.75 → 7.0   (.75 rounds up to whole band)
        ([7.0, 7.0, 6.5, 6.5], 7.0),  # avg 6.75 → 7.0
        ([6.0, 6.0, 6.0, 6.5], 6.0),  # avg 6.125 → 6.0
    ],
)
def test_overall_band_official_rounding(bands, expected):
    assert overall_band(bands) == expected


async def tables(db) -> dict[str, list[dict]]:
    async with db() as session:
        return {t.skill: t.rows for t in await session.scalars(select(BandTable).where(BandTable.is_active))}


async def test_seeded_tables_match_official_anchors(db):
    t = await tables(db)
    # ielts.org anchors (RESEARCH §4)
    for raw, band in [(16, 5), (23, 6), (30, 7), (35, 8)]:
        assert band_for_raw(t["listening"], raw) == (band, False)
    for raw, band in [(15, 5), (23, 6), (30, 7), (35, 8)]:
        assert band_for_raw(t["reading_academic"], raw) == (band, False)


async def test_tables_cover_every_raw_score_once_and_are_monotonic(db):
    for rows in (await tables(db)).values():
        bands = []
        for raw in range(41):
            assert sum(r["min_raw"] <= raw <= r["max_raw"] for r in rows) == 1, raw
            bands.append(band_for_raw(rows, raw)[0])
        assert bands == sorted(bands)


async def test_below_table_is_flagged_estimate(db):
    t = await tables(db)
    assert band_for_raw(t["listening"], 5)[1] is True
    with pytest.raises(ValueError):
        band_for_raw(t["listening"], 41)
