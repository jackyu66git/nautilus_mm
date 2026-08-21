"""T0 vs frozen zg/zd. No ATR bins. No EMA."""
from __future__ import annotations

from chan_1st_point_fate.scan import scan_first
from chan_2nd_point_fate.scan import scan_second
from chan_cont_null.scan import load_events


def region(pos: float) -> str:
    if pos < 0:
        return "OUT_LOW"
    if pos > 1:
        return "OUT_HIGH"
    return "IN"


def pos_of(close: float, zg: float, zd: float) -> float | None:
    w = zg - zd
    if w <= 0:
        return None
    return (close - zd) / w


def boxes_from_scans(bar) -> dict[str, dict]:
    first = {e["event_id"]: e for e in scan_first(bar)["events"]}
    second = {e["event_id"]: e for e in scan_second(bar)["events"]}
    return {**first, **second}
