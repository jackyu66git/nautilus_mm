"""Phase 0 field lock. Historical leftover anchors. No replay. No HTF BSP."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Literal

RailName = Literal["ZG", "ZD", "GG", "DD"]
RailSide = Literal["ABOVE", "CONTACT", "BELOW"]

FORBIDDEN_LEDGER_KEYS = frozenset(
    {
        "HTF_B1",
        "HTF_B2",
        "HTF_BSP",
        "b1_b2_rate",
        "WR",
        "PF",
        "win_rate",
        "Entry",
        "SMC",
        "pos",
        "NEAR",
        "combo_score",
        "MFE",
        "MAE",
    }
)

REPORT_FIELDS = (
    "T_ZG",
    "T_ZD",
    "T_GG",
    "T_DD",
    "T_ZS_COMPLETE",
    "T_LTF_B1",
    "zg",
    "zd",
    "gg",
    "dd",
    "side_zg",
    "side_zd",
    "side_gg",
    "side_dd",
    "NO_HIST_ANCHOR",
)


@dataclass(frozen=True)
class Phase0Row:
    T_LTF_B1: object | None
    LTF_B1: object | None
    zs_id: object | None
    T_ZG: object | None
    T_ZD: object | None
    T_GG: object | None
    T_DD: object | None
    T_ZS_COMPLETE: object | None
    zg: float | None
    zd: float | None
    gg: float | None
    dd: float | None
    zg_unchanged: bool | None
    zd_unchanged: bool | None
    gg_unchanged: bool | None
    dd_unchanged: bool | None
    side_zg: RailSide | None
    side_zd: RailSide | None
    side_gg: RailSide | None
    side_dd: RailSide | None
    NO_HIST_ANCHOR: bool | None


def assert_no_htf_bsp(record: dict) -> None:
    hit = FORBIDDEN_LEDGER_KEYS.intersection(record)
    if hit:
        raise ValueError(f"CHAN_HTF_HIST_ANCHOR ledger polluted: {sorted(hit)}")


def is_historical(*, has_next: bool, t_complete, t_b1) -> bool:
    """Leftover completed before B1. Living current box is not this object."""
    if not has_next or t_complete is None or t_b1 is None:
        return False
    return t_complete < t_b1


def rail_side(low: float, high: float, level: float) -> RailSide:
    if high < level:
        return "BELOW"
    if low > level:
        return "ABOVE"
    return "CONTACT"


def phase0_field_names() -> tuple[str, ...]:
    return tuple(f.name for f in fields(Phase0Row))
