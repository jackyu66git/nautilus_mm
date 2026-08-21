"""CHAN_SETUP_STRATA_001 vocabulary lock. Birth-time X only. No scan."""
from __future__ import annotations

from typing import Any

SPACE_RELS = (
    "CONTACT_BOX",
    "ABOVE_BOX",
    "BELOW_BOX",
    "STRADDLE_BOX",
)

BI_STATES = (
    "UP_SURE",
    "UP_UNSURE",
    "DOWN_SURE",
    "DOWN_UNSURE",
    "BI_DIR_NONE",
)

FX_SIDES = ("TOP", "BOTTOM")

OUTCOME_CLASSES = (
    "CONTINUES",
    "REVERSES",
    "DISSOLVES",
    "NEXT_EVENT",
    "CENSOR",
)

SIDES = frozenset({"ABOVE", "CONTACT", "BELOW"})
DIRS = frozenset({"UP", "DOWN"})

FORBIDDEN_STRATA_KEYS = frozenset(
    {
        "MFE",
        "MAE",
        "WR",
        "PF",
        "expectancy",
        "Entry",
        "Stop",
        "allow",
        "success",
        "fail",
        "hit_rate",
        "p_value",
        "NEW_SETUP",
        "of_kline_delta",
        "of_hhi",
        "of_push",
        "smc_state",
        "label_b1",
        "B2",
        "NEAR",
        "pos",
        "side_gg",
        "side_dd",
        "htf_living",
        "T_FX_VISIBLE",
    }
)


def latest_leftover(leftover: list[dict] | None) -> dict | None:
    if not leftover:
        return None
    return max(leftover, key=lambda z: str(z.get("T_ZS_COMPLETE") or ""))


def space_rel(leftover: list[dict] | None) -> str:
    latest = latest_leftover(leftover)
    if latest is None:
        return "STRADDLE_BOX"
    zg = latest.get("side_zg")
    zd = latest.get("side_zd")
    if zg == "CONTACT" or zd == "CONTACT":
        return "CONTACT_BOX"
    if zg == "ABOVE" and zd == "ABOVE":
        return "ABOVE_BOX"
    if zg == "BELOW" and zd == "BELOW":
        return "BELOW_BOX"
    return "STRADDLE_BOX"


def bi_state(bi_dir: Any, bi_sure: Any) -> str:
    if bi_dir not in DIRS:
        return "BI_DIR_NONE"
    sure = bi_sure is True
    if bi_dir == "UP":
        return "UP_SURE" if sure else "UP_UNSURE"
    return "DOWN_SURE" if sure else "DOWN_UNSURE"
