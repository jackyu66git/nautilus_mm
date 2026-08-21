"""V2 TP variants. Same Entry/Stop/Time as V1. No EMA. No ATR."""
from __future__ import annotations

import pandas as pd

from chan_b3_v2.paths import BAR_H, RISK_FRAC, TIME_BARS


def simulate_one(ev: dict, bar: pd.DataFrame, account: float, tp_mult: float) -> dict:
    i0 = int(ev["tape_row"])
    n = len(bar)
    kind = ev["kind"]
    buy = kind == "B3"
    zg, zd = float(ev["zg"]), float(ev["zd"])
    risk_usdt = account * RISK_FRAC
    base = {
        "event_id": ev["event_id"],
        "kind": kind,
        "side": "LONG" if buy else "SHORT",
        "tape_row": i0,
        "zg": zg,
        "zd": zd,
        "tp_mult": tp_mult,
        "t0_close": float(bar.iloc[i0]["close"]),
    }
    i1 = i0 + 1
    if i1 >= n:
        return {**base, "outcome": "CENSOR", "reason": "NO_T1", "r_mult": None, "pnl_usdt": 0.0}

    entry = float(bar.iloc[i1]["open"])
    stop = zd if buy else zg
    r_px = (entry - stop) if buy else (stop - entry)
    if r_px <= 0:
        return {
            **base,
            "entry": entry,
            "stop": stop,
            "tp": None,
            "r_px": r_px,
            "outcome": "SKIP",
            "reason": "ENTRY_THROUGH_STOP",
            "r_mult": None,
            "pnl_usdt": 0.0,
        }

    tp = entry + tp_mult * r_px if buy else entry - tp_mult * r_px
    last = min(i1 + TIME_BARS - 1, n - 1)
    horizon_ok = (last - i1 + 1) >= TIME_BARS
    high = bar["high"].to_numpy(float)
    low = bar["low"].to_numpy(float)
    close = bar["close"].to_numpy(float)

    def fav(px_hi: float, px_lo: float) -> float:
        return (px_hi - entry) if buy else (entry - px_lo)

    def adv(px_hi: float, px_lo: float) -> float:
        return (entry - px_lo) if buy else (px_hi - entry)

    mfe_px = mae_px = 0.0
    mfe_24 = mae_24 = 0.0
    outcome = None
    exit_i = last
    exit_px = float(close[last])
    same_bar_both = False
    reason = None

    for k in range(i1, last + 1):
        mfe_24 = max(mfe_24, fav(high[k], low[k]))
        mae_24 = max(mae_24, adv(high[k], low[k]))
        if outcome is None:
            mfe_px = max(mfe_px, fav(high[k], low[k]))
            mae_px = max(mae_px, adv(high[k], low[k]))
            hit_tp = (high[k] >= tp) if buy else (low[k] <= tp)
            hit_stop = (low[k] <= stop) if buy else (high[k] >= stop)
            if hit_tp and hit_stop:
                same_bar_both = True
                outcome, exit_i, exit_px, reason = "LOSS", k, stop, "SAME_BAR_BOTH"
            elif hit_stop:
                outcome, exit_i, exit_px, reason = "LOSS", k, stop, "STOP"
            elif hit_tp:
                outcome, exit_i, exit_px, reason = "WIN", k, tp, "TP"

    if outcome is None:
        if horizon_ok:
            outcome, reason = "TIME_EXIT", "TIME_24H"
        else:
            outcome, reason = "CENSOR", "END_OF_TAPE"
        exit_px = float(close[exit_i])

    if buy:
        r_mult = (exit_px - entry) / r_px
    else:
        r_mult = (entry - exit_px) / r_px
    if outcome == "WIN":
        r_mult = float(tp_mult)
    if outcome == "LOSS":
        r_mult = -1.0

    return {
        **base,
        "entry": entry,
        "stop": stop,
        "tp": tp,
        "r_px": round(r_px, 4),
        "entry_ts": str(bar.iloc[i1]["open_ts"]),
        "exit_ts": str(bar.iloc[exit_i]["close_ts"]),
        "exit_row": int(exit_i),
        "exit_px": exit_px,
        "outcome": outcome,
        "reason": reason,
        "same_bar_both": same_bar_both,
        "hours_to_exit": round((exit_i - i1) * BAR_H, 4),
        "r_mult": round(r_mult, 6),
        "pnl_usdt": round(r_mult * risk_usdt, 4),
        "mfe_r": round(mfe_px / r_px, 6),
        "mae_r": round(mae_px / r_px, 6),
        "mfe_24h_r": round(mfe_24 / r_px, 6),
        "mae_24h_r": round(mae_24 / r_px, 6),
        "horizon_ok": horizon_ok,
        "risk_usdt": risk_usdt,
    }
