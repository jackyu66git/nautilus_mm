"""Census lock. Observation-state inventory only."""
from __future__ import annotations

CENSUS_EVENT_FIELDS = (
    "setup_id",
    "T_SETUP_VISIBLE",
    "T_SETUP_END",
    "duration_bars",
    "duration_hours",
    "htf_anchor_count",
    "ltf_fx",
    "tape_row",
)

FORBIDDEN_CENSUS_KEYS = frozenset(
    {
        "MFE",
        "MAE",
        "WR",
        "PF",
        "expectancy",
        "Entry",
        "Stop",
        "allow",
        "B1",
        "B2",
        "b1_lock",
        "b1_lock_id",
        "of_kline_delta",
        "of_hhi",
        "of_push",
        "of_speed",
        "of_support",
        "smc_state",
        "CONTACT",
        "side_zg",
        "T_FX_VISIBLE",
        "htf_living",
    }
)


def assert_census_clean(record: dict) -> None:
    hit = FORBIDDEN_CENSUS_KEYS.intersection(record)
    if hit:
        raise ValueError(f"census polluted: {sorted(hit)}")
    extra = set(record) - set(CENSUS_EVENT_FIELDS)
    if extra:
        raise ValueError(f"census extra keys: {sorted(extra)}")
