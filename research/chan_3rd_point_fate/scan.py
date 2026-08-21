"""Fate after frozen 15m 3rd points. No EMA. No OF."""
from __future__ import annotations

import pandas as pd

from chan_ema52_where.scan import _ts


def follow_fate(ev: dict, bar: pd.DataFrame) -> dict:
    i0 = int(ev["tape_row"])
    n = len(bar)
    close = bar["close"].to_numpy(float)
    high = bar["high"].to_numpy(float)
    low = bar["low"].to_numpy(float)
    zg, zd = float(ev["zg"]), float(ev["zd"])
    kind = ev["kind"]
    ref_hi = float(high[i0])
    ref_lo = float(low[i0])
    fate = "CENSOR"
    end_i = n - 1
    for k in range(i0 + 1, n):
        if kind == "B3":
            if close[k] < zd:
                fate, end_i = "REVERSE", k
                break
            if zd <= close[k] <= zg:
                fate, end_i = "REENTRY", k
                break
            if high[k] > ref_hi:
                fate, end_i = "RESUME", k
                break
        else:
            if close[k] > zg:
                fate, end_i = "REVERSE", k
                break
            if zd <= close[k] <= zg:
                fate, end_i = "REENTRY", k
                break
            if low[k] < ref_lo:
                fate, end_i = "RESUME", k
                break
    return {
        "event_id": ev["event_id"],
        "kind": kind,
        "T_3_VISIBLE": ev["T_3_VISIBLE"],
        "T_FATE": _ts(bar, end_i),
        "fate": fate,
        "hours_to_fate": round((end_i - i0) * 0.25, 4),  # latency, not duration
    }
