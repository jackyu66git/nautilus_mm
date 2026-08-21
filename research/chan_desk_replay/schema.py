"""Visible-state ledger lock. No interpretation. No trade. No future."""
from __future__ import annotations

from typing import Literal

FORBIDDEN_LEDGER_KEYS = frozenset(
    {
        "allow",
        "Allow",
        "entry",
        "Entry",
        "stop",
        "Stop",
        "target",
        "Target",
        "MFE",
        "MAE",
        "of_support",
        "of_against",
        "of_confirm",
        "smc_valid",
        "smc_event",
        "B2",
        "LTF_B2",
        "HTF_B1",
        "HTF_B2",
        "HTF_BSP",
        "WR",
        "PF",
        "win_rate",
        "combo_score",
        "NEAR",
        "pos",
    }
)

SMC_STATE: Literal["UNDEFINED"] = "UNDEFINED"

TAPE_FIELDS = (
    "t",
    "open_ts",
    "htf_anchor_count",
    "htf_leftover",
    "htf_living",
    "ltf_bi_dir",
    "ltf_bi_sure",
    "ltf_fx",
    "ltf_fx_id",
    "T_FX_VISIBLE",
    "b1_lock",
    "b1_lock_id",
    "of_kline_delta",
    "of_kline_volume",
    "of_trade_status",
    "of_trade_n",
    "of_trade_delta",
    "of_hhi",
    "of_push",
    "of_speed",
    "of_window_end",
    "smc_state",
)


def assert_clean(record: dict) -> None:
    hit = FORBIDDEN_LEDGER_KEYS.intersection(record)
    if hit:
        raise ValueError(f"CHAN_DESK_REPLAY ledger polluted: {sorted(hit)}")
    if record.get("smc_state") != SMC_STATE:
        raise ValueError("smc_state must be UNDEFINED")
