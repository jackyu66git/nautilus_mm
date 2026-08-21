"""Exit geometry. Same Entry/Stop as V1. No PnL. No ATR."""
from __future__ import annotations

import pandas as pd

from chan_b3_exit_census.paths import BAR_H, BARS_PER_H, HORIZON_H, R_GRID


def _fav(buy: bool, entry: float, hi: float, lo: float) -> float:
    return (hi - entry) if buy else (entry - lo)


def scan_one(ev: dict, bar: pd.DataFrame) -> dict:
    i0 = int(ev["tape_row"])
    n = len(bar)
    kind = ev["kind"]
    buy = kind == "B3"
    zg, zd = float(ev["zg"]), float(ev["zd"])
    i1 = i0 + 1
    if i1 >= n:
        return {"event_id": ev["event_id"], "kind": kind, "outcome": "CENSOR", "reason": "NO_T1"}
    entry = float(bar.iloc[i1]["open"])
    stop = zd if buy else zg
    r_px = (entry - stop) if buy else (stop - entry)
    if r_px <= 0:
        return {
            "event_id": ev["event_id"],
            "kind": kind,
            "side": "LONG" if buy else "SHORT",
            "entry": entry,
            "stop": stop,
            "r_px": r_px,
            "outcome": "SKIP",
            "reason": "ENTRY_THROUGH_STOP",
        }

    high = bar["high"].to_numpy(float)
    low = bar["low"].to_numpy(float)
    stop_i = None
    first_r: dict[float, int] = {}
    mfe_px = 0.0
    mfe_i = i1
    mfe_at = {h: 0.0 for h in HORIZON_H}
    for k in range(i1, n):
        fav = _fav(buy, entry, float(high[k]), float(low[k]))
        if fav > mfe_px:
            mfe_px, mfe_i = fav, k
        for h in HORIZON_H:
            if (k - i1) < h * BARS_PER_H:
                mfe_at[h] = max(mfe_at[h], fav)
        hit_stop = (float(low[k]) <= stop) if buy else (float(high[k]) >= stop)
        if stop_i is None and hit_stop:
            stop_i = k
        for r in R_GRID:
            if r not in first_r and fav >= r * r_px:
                first_r[r] = k
        if stop_i is not None:
            break

    hours_available = round((n - 1 - i1) * BAR_H, 4)
    hours_to_stop = None if stop_i is None else round((stop_i - i1) * BAR_H, 4)

    def status_at(r: float, last_i: int | None) -> dict:
        hit_i = first_r.get(r)
        cap = last_i if last_i is not None else n - 1
        hit_ok = hit_i is not None and hit_i <= cap
        stop_ok = stop_i is not None and stop_i <= cap
        if hit_ok and stop_ok and hit_i == stop_i:
            st = "STOP_FIRST"
        elif stop_ok and (not hit_ok or stop_i < hit_i):
            st = "STOP_FIRST"
        elif hit_ok:
            st = "HIT"
        elif last_i is None and stop_i is None:
            st = "CENSOR"
        else:
            st = "NONE"
        hours = None if hit_i is None or st != "HIT" else round((hit_i - i1) * BAR_H, 4)
        return {"status": st, "hours": hours}

    levels = {str(r): status_at(r, None) for r in R_GRID}
    by_h = {}
    for h in HORIZON_H:
        last_i = min(i1 + h * BARS_PER_H - 1, n - 1)
        by_h[str(h)] = {str(r): status_at(r, last_i)["status"] for r in R_GRID}

    return {
        "event_id": ev["event_id"],
        "kind": kind,
        "side": "LONG" if buy else "SHORT",
        "tape_row": i0,
        "entry": entry,
        "stop": stop,
        "r_px": round(r_px, 4),
        "hours_available": hours_available,
        "hours_to_stop": hours_to_stop,
        "mfe_r": round(mfe_px / r_px, 6),
        "hours_to_mfe": round((mfe_i - i1) * BAR_H, 4),
        "mfe_24h_r": round(mfe_at[24] / r_px, 6),
        "mfe_48h_r": round(mfe_at[48] / r_px, 6),
        "mfe_72h_r": round(mfe_at[72] / r_px, 6),
        "levels": levels,
        "by_h": by_h,
    }
