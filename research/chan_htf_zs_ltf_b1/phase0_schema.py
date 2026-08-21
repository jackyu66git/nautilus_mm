"""Phase 0 field lock. No replay. No HTF BSP."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Literal

SpatialBucket = Literal["INSIDE", "BOUNDARY_CONTACT", "OUTSIDE"]

REPORT_FIELDS = (
    "T_HTF_ZS_VISIBLE",
    "T_LTF_B1",
    "delta_t",
    "ZS_birth_bar",
    "B1_bar",
    "ZS_valid_at_B1",
    "zg_at_visibility",
    "zd_at_visibility",
    "zg_at_B1",
    "zd_at_B1",
)

FORBIDDEN_LEDGER_KEYS = frozenset({"HTF_B1", "HTF_B2", "HTF_BSP"})


@dataclass(frozen=True)
class Phase0Row:
    T_HTF_ZS_VISIBLE: object | None
    T_LTF_B1: object | None
    delta_t: object | None
    ZS_birth_bar: object | None
    B1_bar: object | None
    ZS_valid_at_B1: bool | None
    zg_at_visibility: float | None
    zd_at_visibility: float | None
    zg_at_B1: float | None
    zd_at_B1: float | None
    zs_id: object | None = None
    zs_present_at_b1: bool | None = None
    zs_living_at_b1: bool | None = None
    zs_leftover_at_b1: bool | None = None
    zg_zd_unchanged: bool | None = None
    ZS_EXPAND: bool | None = None
    spatial_bucket: SpatialBucket | None = None
    pos: float | None = None
    NO_HTF_ZS: bool | None = None


def assert_no_htf_bsp(record: dict) -> None:
    hit = FORBIDDEN_LEDGER_KEYS.intersection(record)
    if hit:
        raise ValueError(f"HTF BSP polluted ledger: {sorted(hit)}")


def living_at_b1(*, present: bool, has_next: bool, zg_zd_unchanged: bool) -> bool:
    """Living space, not leftover box. is_sure is not part of this gate."""
    return present and (not has_next) and zg_zd_unchanged


def spatial_bucket(low: float, high: float, zd: float, zg: float) -> SpatialBucket:
    if zg <= zd:
        raise ValueError("invalid zs range")
    if high < zd or low > zg:
        return "OUTSIDE"
    if low > zd and high < zg:
        return "INSIDE"
    return "BOUNDARY_CONTACT"


def phase0_field_names() -> tuple[str, ...]:
    return tuple(f.name for f in fields(Phase0Row))
