"""Trend-only pullbacks × EMA52 buckets. EMA params frozen from WHERE_001."""
from __future__ import annotations

import pandas as pd

from chan_ema52_state.paths import AWAY_K, CHECKPOINT, NEAR_K, WARM
from chan_ema52_state.state import living_id, market_state
from chan_ema52_where.scan import add_indicators, _ts
from chan_htf_zs_ltf_b1.replay import bars_to_df
from chanlun.pipeline.timeframe import TF_DF

TREND = {"TREND_UP", "TREND_DOWN"}


def label_htf(bar_1h: pd.DataFrame) -> tuple[list[str], list[str | None]]:
    df = bars_to_df(bar_1h)
    tf = TF_DF()
    tf.init_stream(df.iloc[:1], interval=1, timeframe="1h")
    states: list[str] = []
    zids: list[str | None] = []

    def cap(i: int) -> None:
        row = bar_1h.iloc[i]
        states.append(
            market_state(
                tf.bi_zs_list,
                float(row["close"]),
                float(row["high"]),
                float(row["low"]),
            )
        )
        zids.append(living_id(tf.bi_zs_list))
        if tf.bsp_list:
            raise RuntimeError("HTF path emitted bsp_list")

    cap(0)
    print(f"HTF state 1/{len(df)}", flush=True)
    for i in range(1, len(df)):
        tf.append_bar(df.iloc[i])
        cap(i)
        if i % 200 == 0 or i + 1 == len(df):
            print(f"HTF state {i + 1}/{len(df)}", flush=True)
    return states, zids


def _bucket(crossed: bool, min_dist: float) -> str:
    if crossed:
        return "CROSS"
    if min_dist <= NEAR_K:
        return "NEAR"
    if min_dist <= AWAY_K:
        return "MID"
    return "FAR"


def _dist_up(low, ema, atr) -> float:
    return (low - ema) / atr


def _dist_down(high, ema, atr) -> float:
    return (ema - high) / atr


def scan_trend_pullbacks(bar: pd.DataFrame, states: list[str], zids: list[str | None]) -> list[dict]:
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
        rec["end_state"] = states[i]
        out.append(rec)
        open_ep = None

    def locate(ep: dict, i: int) -> None:
        srow = ep["swing_row"]
        side = ep["side"]
        crossed = False
        dists = []
        for j in range(srow, i + 1):
            if not (atr[j] > 0):
                continue
            if side == "UP":
                if low[j] < ema[j]:
                    crossed = True
                dists.append(_dist_up(low[j], ema[j], atr[j]))
            else:
                if high[j] > ema[j]:
                    crossed = True
                dists.append(_dist_down(high[j], ema[j], atr[j]))
        if not dists:
            return
        ep["bucket"] = _bucket(crossed, min(dists))
        ep["min_dist_atr"] = float(min(dists))

    for i in range(WARM, n):
        if not (atr[i] > 0):
            continue
        st = states[i]
        if open_ep is not None:
            ep = open_ep
            if ep["side"] == "UP":
                if high[i] > ep["peak"]:
                    finish(i, "RESUME")
                elif st == "TREND_DOWN":
                    finish(i, "REVERSE")
                elif st == "RANGE":
                    finish(i, "RANGE_REENTRY")
                elif zids[i] is not None and zids[i] != ep["living_at_swing"] and st != "RANGE":
                    finish(i, "NEW_ZS")
            else:
                if low[i] < ep["peak"]:
                    finish(i, "RESUME")
                elif st == "TREND_UP":
                    finish(i, "REVERSE")
                elif st == "RANGE":
                    finish(i, "RANGE_REENTRY")
                elif zids[i] is not None and zids[i] != ep["living_at_swing"] and st != "RANGE":
                    finish(i, "NEW_ZS")
            if open_ep is None:
                continue
            age = i - open_ep["swing_row"]
            if age == CHECKPOINT and open_ep.get("bucket") is None:
                locate(open_ep, i)
                open_ep["T_CHECKPOINT"] = _ts(d, i)
                open_ep["checkpoint_state"] = states[i]

        if open_ep is not None:
            continue
        if i < 2 or st not in TREND:
            continue
        if st == "TREND_UP" and high[i - 1] >= high[i - 2] and high[i - 1] > high[i]:
            open_ep = {
                "side": "UP",
                "state_at_swing": st,
                "peak": float(high[i - 1]),
                "swing_row": i,
                "T_SWING_VISIBLE": _ts(d, i),
                "living_at_swing": zids[i],
                "bucket": None,
                "min_dist_atr": None,
                "T_CHECKPOINT": None,
                "checkpoint_state": None,
            }
        elif st == "TREND_DOWN" and low[i - 1] <= low[i - 2] and low[i - 1] < low[i]:
            open_ep = {
                "side": "DOWN",
                "state_at_swing": st,
                "peak": float(low[i - 1]),
                "swing_row": i,
                "T_SWING_VISIBLE": _ts(d, i),
                "living_at_swing": zids[i],
                "bucket": None,
                "min_dist_atr": None,
                "T_CHECKPOINT": None,
                "checkpoint_state": None,
            }

    if open_ep is not None:
        finish(n - 1, "CENSOR")
    return out
