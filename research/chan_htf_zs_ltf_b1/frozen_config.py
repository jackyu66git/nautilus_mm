"""CHAN_HTF_ZS_LTF_B1_001 Phase 0. No B1→B2 rate. No HTF BSP. No OF/SMC."""
from __future__ import annotations

FORBIDDEN_LEDGER_KEYS = frozenset(
    {
        "HTF_B1",
        "HTF_B2",
        "HTF_BSP",
        "WR",
        "PF",
        "win_rate",
        "profit_factor",
        "Entry",
        "SMC",
        "absorption_flag",
        "b1_b2_rate",
        "label_B2",
    }
)

# Phase 0 existence only. Not a trading threshold. Not a B1→B2 floor.
P0_MIN_B1 = 1


def assert_clean(record: dict) -> None:
    hit = FORBIDDEN_LEDGER_KEYS.intersection(record)
    if hit:
        raise ValueError(f"CHAN_HTF_ZS_LTF_B1_001 ledger polluted: {sorted(hit)}")
