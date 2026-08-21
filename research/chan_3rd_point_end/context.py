"""1H pre-T3 context. No EMA. No 3rd-point rewrite."""
from __future__ import annotations

import pandas as pd

from chan_3rd_point_end.paths import EARLY_H, LATE_H
from chan_ema52_state.state import living_and_leftover, market_state
from chan_ema52_where.scan import add_indicators
from chan_htf_zs_ltf_b1.replay import bars_to_df
from chanlun.pipeline.timeframe import TF_DF


def _ts(bar, i) -> pd.Timestamp:
    ts = pd.Timestamp(bar.iloc[i]["close_ts"])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def segment(state: str, age_h: float) -> str:
    if state in ("RANGE", "TRANSITION"):
        return "SHIFT"
    if state not in ("TREND_UP", "TREND_DOWN"):
        return "NONE"
    if age_h < EARLY_H:
        return "EARLY"
    if age_h < LATE_H:
        return "MID"
    return "LATE"


def stream_htf(bar_1h: pd.DataFrame) -> list[dict]:
    d = add_indicators(bar_1h)
    df = bars_to_df(bar_1h)
    tf = TF_DF()
    tf.init_stream(df.iloc[:1], interval=1, timeframe="1h")
    out: list[dict] = []
    prev = None
    age = 0.0
    start_close = float(d.iloc[0]["close"])

    def cap(i: int) -> None:
        nonlocal prev, age, start_close
        row = d.iloc[i]
        close, high, low = float(row["close"]), float(row["high"]), float(row["low"])
        atr = float(row["atr"]) if row["atr"] == row["atr"] else 0.0
        st = market_state(tf.bi_zs_list, close, high, low)
        living, leftover = living_and_leftover(tf.bi_zs_list)
        box = living if living is not None else leftover
        zg = float(box.zg) if box is not None and box.zg is not None else None
        zd = float(box.zd) if box is not None and box.zd is not None else None
        if st in ("TREND_UP", "TREND_DOWN") and st == prev:
            age += 1.0
        elif st in ("TREND_UP", "TREND_DOWN"):
            age = 1.0
            start_close = close
        else:
            age = 0.0
        prev = st
        run = 0.0
        if atr > 0 and st == "TREND_UP":
            run = (close - start_close) / atr
        elif atr > 0 and st == "TREND_DOWN":
            run = (start_close - close) / atr
        out.append(
            {
                "close_ts": _ts(bar_1h, i),
                "state": st,
                "age_h": age,
                "segment": segment(st, age),
                "zg": zg,
                "zd": zd,
                "atr": atr,
                "close": close,
                "run_atr": round(run, 4),
            }
        )

    cap(0)
    print(f"HTF end-ctx 1/{len(df)}", flush=True)
    for i in range(1, len(df)):
        tf.append_bar(df.iloc[i])
        cap(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(f"HTF end-ctx {i + 1}/{len(df)}", flush=True)
        if tf.bsp_list:
            raise RuntimeError("HTF emitted bsp_list")
    return out


def htf_at(snaps: list[dict], t3: pd.Timestamp) -> dict | None:
    t3 = pd.Timestamp(t3)
    if t3.tzinfo is None:
        t3 = t3.tz_localize("UTC")
    else:
        t3 = t3.tz_convert("UTC")
    chosen = None
    for s in snaps:
        if s["close_ts"] <= t3:
            chosen = s
        else:
            break
    return chosen


def box_dist(kind: str, px: float, zg, zd, atr: float) -> float | None:
    if zg is None or zd is None or not (atr > 0):
        return None
    if kind == "B3":
        return round((px - zg) / atr, 4)
    return round((zd - px) / atr, 4)
