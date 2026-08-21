"""1H Chan market state. Living box, no future leftover rewrite."""
from __future__ import annotations


def living_and_leftover(zs_list):
    living = None
    leftover = None
    for zs in zs_list:
        if zs.zg is None or zs.zd is None:
            continue
        if getattr(zs, "next", None) is None:
            living = zs
        else:
            leftover = zs
    return living, leftover


def living_id(zs_list) -> str | None:
    living, _ = living_and_leftover(zs_list)
    if living is None:
        return None
    return str(living.start_bi.start_time)


def market_state(zs_list, close: float, high: float, low: float) -> str:
    living, leftover = living_and_leftover(zs_list)
    box = living if living is not None else leftover
    if box is None:
        return "NONE"
    zg, zd = float(box.zg), float(box.zd)
    if zg <= zd:
        return "NONE"
    inside = zd <= close <= zg
    if living is not None:
        if inside:
            return "RANGE"
        overlaps = low <= zg and high >= zd
        if overlaps:
            return "TRANSITION"
        if close > zg:
            return "TREND_UP"
        return "TREND_DOWN"
    if inside:
        return "TRANSITION"
    if close > zg:
        return "TREND_UP"
    return "TREND_DOWN"
