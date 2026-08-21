"""After frozen 15m 3rd points: next pullback vs EMA52, then structural fate."""
from __future__ import annotations

import pandas as pd

from chan_3buy_ema52.paths import NEAR_K
from chan_ema52_where.scan import add_indicators, _ts


def _entered(min_dist: float, crossed: bool) -> bool:
    return crossed or min_dist <= NEAR_K


def _next_pullback(i0: int, side: str, low, high, n: int) -> int | None:
    for j in range(i0 + 2, n):
        if side == "B3":
            if low[j - 1] <= low[j - 2] and low[j - 1] < low[j]:
                return j
        else:
            if high[j - 1] >= high[j - 2] and high[j - 1] > high[j]:
                return j
    return None


def follow_event(ev: dict, bar: pd.DataFrame) -> dict:
    d = bar
    i0 = int(ev["tape_row"])
    n = len(d)
    close = d["close"].to_numpy(float)
    high = d["high"].to_numpy(float)
    low = d["low"].to_numpy(float)
    ema = d["ema"].to_numpy(float)
    atr = d["atr"].to_numpy(float)
    zg, zd = float(ev["zg"]), float(ev["zd"])
    kind = ev["kind"]
    rec = {
        "event_id": ev["event_id"],
        "kind": kind,
        "T_3_VISIBLE": ev["T_3_VISIBLE"],
        "T_PB_VISIBLE": None,
        "T_END": None,
        "entered": None,
        "min_dist_atr": None,
        "fate": "NO_PULLBACK",
        "hours_to_end": None,
    }
    pb = _next_pullback(i0, kind, low, high, n)
    if pb is None:
        rec["T_END"] = _ts(d, n - 1)
        return rec
    rec["T_PB_VISIBLE"] = _ts(d, pb)
    crossed = False
    dists = []
    for j in range(i0 + 1, pb + 1):
        if not (atr[j] > 0):
            continue
        if kind == "B3":
            if low[j] < ema[j]:
                crossed = True
            dists.append((low[j] - ema[j]) / atr[j])
        else:
            if high[j] > ema[j]:
                crossed = True
            dists.append((ema[j] - high[j]) / atr[j])
    min_dist = min(dists) if dists else 99.0
    rec["min_dist_atr"] = float(min_dist)
    rec["entered"] = _entered(min_dist, crossed)
    run_ext = float(high[i0:pb].max()) if kind == "B3" else float(low[i0:pb].min())
    fate = "CENSOR"
    end_i = n - 1
    for k in range(pb + 1, n):
        if kind == "B3":
            if high[k] > run_ext:
                fate, end_i = "RESUME", k
                break
            if close[k] < zd:
                fate, end_i = "REVERSE", k
                break
            if zd <= close[k] <= zg:
                fate, end_i = "REENTRY", k
                break
        else:
            if low[k] < run_ext:
                fate, end_i = "RESUME", k
                break
            if close[k] > zg:
                fate, end_i = "REVERSE", k
                break
            if zd <= close[k] <= zg:
                fate, end_i = "REENTRY", k
                break
    rec["fate"] = fate
    rec["T_END"] = _ts(d, end_i)
    rec["hours_to_end"] = round((end_i - pb) * 0.25, 4)
    return rec


def follow_all(events: list[dict], bar_15m: pd.DataFrame) -> list[dict]:
    d = add_indicators(bar_15m)
    return [follow_event(ev, d) for ev in events]
