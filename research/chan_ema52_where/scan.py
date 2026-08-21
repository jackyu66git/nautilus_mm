"""1H EMA52 WHERE. No MACD. No Chan BSP. No P&L."""
from __future__ import annotations

import pandas as pd

from chan_ema52_where.paths import (
    ATR_SPAN,
    AWAY_K,
    CHECKPOINT,
    EMA_SPAN,
    NEAR_K,
    TREND_BARS,
    WARM,
)


def add_indicators(bar: pd.DataFrame) -> pd.DataFrame:
    d = bar.copy()
    c = d["close"].astype(float)
    h = d["high"].astype(float)
    l = d["low"].astype(float)
    d["ema"] = c.ewm(span=EMA_SPAN, adjust=False).mean()
    prev = c.shift(1)
    tr = pd.concat([(h - l), (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(span=ATR_SPAN, adjust=False).mean()
    return d


def _ts(bar: pd.DataFrame, i: int) -> str:
    ts = pd.Timestamp(bar.iloc[i]["close_ts"])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return str(ts)


def _trend_side(close, ema, i: int) -> str | None:
    if i < TREND_BARS:
        return None
    ups = all(close[i - k] > ema[i - k] for k in range(TREND_BARS))
    dns = all(close[i - k] < ema[i - k] for k in range(TREND_BARS))
    if ups and ema[i] > ema[i - 1]:
        return "UP"
    if dns and ema[i] < ema[i - 1]:
        return "DOWN"
    return None


def scan_episodes(bar: pd.DataFrame) -> list[dict]:
    d = add_indicators(bar)
    close = d["close"].to_numpy(float)
    high = d["high"].to_numpy(float)
    low = d["low"].to_numpy(float)
    ema = d["ema"].to_numpy(float)
    atr = d["atr"].to_numpy(float)
    n = len(d)
    open_ep: dict | None = None
    out: list[dict] = []

    def finish(i: int, fate: str) -> None:
        nonlocal open_ep
        rec = dict(open_ep)
        rec["T_END"] = _ts(d, i)
        rec["end_row"] = i
        rec["fate"] = fate
        rec["hours_to_end"] = i - rec["swing_row"]
        out.append(rec)
        open_ep = None

    for i in range(WARM, n):
        if not (atr[i] > 0):
            continue
        side = _trend_side(close, ema, i)
        if open_ep is not None:
            ep = open_ep
            if ep["side"] == "UP":
                if close[i] < ema[i]:
                    finish(i, "BREAK")
                elif high[i] > ep["peak"]:
                    finish(i, "RESUME")
                elif (not ep["near"]) and low[i] <= ema[i] + NEAR_K * atr[i] and close[i] >= ema[i]:
                    ep["near"] = True
                    ep["T_NEAR_VISIBLE"] = _ts(d, i)
                    ep["near_row"] = i
                    ep["near_dist_atr"] = float((low[i] - ema[i]) / atr[i])
            else:
                if close[i] > ema[i]:
                    finish(i, "BREAK")
                elif low[i] < ep["peak"]:
                    finish(i, "RESUME")
                elif (not ep["near"]) and high[i] >= ema[i] - NEAR_K * atr[i] and close[i] <= ema[i]:
                    ep["near"] = True
                    ep["T_NEAR_VISIBLE"] = _ts(d, i)
                    ep["near_row"] = i
                    ep["near_dist_atr"] = float((ema[i] - high[i]) / atr[i])
            if open_ep is None:
                continue
            age = i - open_ep["swing_row"]
            if age == CHECKPOINT and open_ep["checkpoint"] is None:
                open_ep["checkpoint"] = "NEAR" if open_ep["near"] else "FAR"
                open_ep["T_CHECKPOINT"] = _ts(d, i)

        if side is None:
            if open_ep is not None:
                finish(i, "CENSOR")
            continue
        if i < 2:
            continue
        if open_ep is not None:
            continue
        if side == "UP" and high[i - 1] >= high[i - 2] and high[i - 1] > high[i]:
            dist = (high[i - 1] - ema[i]) / atr[i]
            if dist >= AWAY_K:
                open_ep = {
                    "side": "UP",
                    "peak": float(high[i - 1]),
                    "swing_row": i,
                    "T_SWING_VISIBLE": _ts(d, i),
                    "away_atr": float(dist),
                    "near": False,
                    "T_NEAR_VISIBLE": None,
                    "near_row": None,
                    "near_dist_atr": None,
                    "checkpoint": None,
                    "T_CHECKPOINT": None,
                }
        elif side == "DOWN" and low[i - 1] <= low[i - 2] and low[i - 1] < low[i]:
            dist = (ema[i] - low[i - 1]) / atr[i]
            if dist >= AWAY_K:
                open_ep = {
                    "side": "DOWN",
                    "peak": float(low[i - 1]),
                    "swing_row": i,
                    "T_SWING_VISIBLE": _ts(d, i),
                    "away_atr": float(dist),
                    "near": False,
                    "T_NEAR_VISIBLE": None,
                    "near_row": None,
                    "near_dist_atr": None,
                    "checkpoint": None,
                    "T_CHECKPOINT": None,
                }

    if open_ep is not None:
        finish(n - 1, "CENSOR")
    return out
