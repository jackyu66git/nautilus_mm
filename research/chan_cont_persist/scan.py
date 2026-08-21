"""Consecutive directional extension chain. Same predicate for events and null."""
from __future__ import annotations

from chan_cont_null.scan import BUY, SELL, event_index, load_events, next_extends  # noqa: F401

HORIZONS = (1, 2, 3, 4)


def chain_ok(high, low, i: int, side: str, h: int) -> bool:
    if h < 1 or i + h >= len(high):
        return False
    for k in range(1, h + 1):
        if side == "BUY":
            if not (float(high[i + k]) > float(high[i + k - 1])):
                return False
        elif not (float(low[i + k]) < float(low[i + k - 1])):
            return False
    return True


def null_chain_rates(high, low, skip: set[int], h: int) -> dict:
    last = len(high) - h
    up = down = n_null = 0
    for i in range(last):
        if i in skip:
            continue
        n_null += 1
        if chain_ok(high, low, i, "BUY", h):
            up += 1
        if chain_ok(high, low, i, "SELL", h):
            down += 1
    return {
        "n_null": n_null,
        "p_up": round(up / n_null, 6) if n_null else None,
        "p_down": round(down / n_null, 6) if n_null else None,
    }
