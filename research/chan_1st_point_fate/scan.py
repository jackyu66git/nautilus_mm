"""Stream engine B1/S1 then structural fate. No new 一类定义. No EMA."""
from __future__ import annotations

import pandas as pd

from chan_ema52_where.scan import _ts
from chan_fractal_of.labels import find_all_bsp_nonesafe
from chan_htf_zs_ltf_b1.replay import WARM, bars_to_df
from chanlun.core.ChanEnum import Chan_BSP_TYPE
from chanlun.pipeline.timeframe import TF_DF

_FIRST = {Chan_BSP_TYPE.B1: "B1", Chan_BSP_TYPE.S1: "S1"}


def scan_first(bar_15m: pd.DataFrame) -> dict:
    df = bars_to_df(bar_15m)
    start = min(WARM, len(df))
    tf = TF_DF()
    tf.init_stream(df.iloc[:start], interval=1, timeframe="15m")
    seen: set[tuple] = set()
    events: list[dict] = []

    def capture(i: int) -> None:
        close = str(_ts(bar_15m, i))
        for bsp in find_all_bsp_nonesafe(tf):
            kind = _FIRST.get(bsp.type)
            if kind is None:
                continue
            leave, zs = bsp.bi, bsp.zs
            members = {str(b.start_time) for b in zs.bi_list}
            if str(leave.start_time) in members:
                continue
            key = (str(zs.start_bi.start_time), str(leave.start_time), kind)
            if key in seen:
                continue
            seen.add(key)
            zg, zd = float(zs.zg), float(zs.zd)
            px = float(bar_15m.iloc[i]["close"])
            events.append(
                {
                    "event_id": f"{zs.start_bi.start_time}:{kind}:{leave.start_time}",
                    "kind": kind,
                    "zs_id": str(zs.start_bi.start_time),
                    "T_1_VISIBLE": close,
                    "zg": zg,
                    "zd": zd,
                    "leave_low": float(leave.low),
                    "leave_high": float(leave.high),
                    "in_box_at_t1": zd <= px <= zg,
                    "tape_row": i,
                }
            )

    capture(start - 1)
    print(f"1st stream {start}/{len(df)}", flush=True)
    for i in range(start, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(f"1st stream {i + 1}/{len(df)} n_1={len(events)}", flush=True)
        if tf.bsp_list:
            raise RuntimeError("LTF emitted bsp_list")
    return {
        "n_15m": len(bar_15m),
        "n_b1": sum(1 for e in events if e["kind"] == "B1"),
        "n_s1": sum(1 for e in events if e["kind"] == "S1"),
        "events": events,
    }


def follow_fate(ev: dict, bar: pd.DataFrame) -> dict:
    """RESUME=事件方向再创新高/低。REVERSE=打穿离开笔。latency 不是持仓。"""
    i0 = int(ev["tape_row"])
    n = len(bar)
    close = bar["close"].to_numpy(float)
    high = bar["high"].to_numpy(float)
    low = bar["low"].to_numpy(float)
    zg, zd = float(ev["zg"]), float(ev["zd"])
    leave_low, leave_high = float(ev["leave_low"]), float(ev["leave_high"])
    kind = ev["kind"]
    in_box = bool(ev["in_box_at_t1"])
    ref_hi, ref_lo = float(high[i0]), float(low[i0])
    fate = "CENSOR"
    end_i = n - 1
    for k in range(i0 + 1, n):
        if kind == "B1":
            if close[k] < leave_low:
                fate, end_i = "REVERSE", k
                break
            if high[k] > ref_hi:
                fate, end_i = "RESUME", k
                break
            if (not in_box) and zd <= close[k] <= zg:
                fate, end_i = "REENTRY", k
                break
        else:
            if close[k] > leave_high:
                fate, end_i = "REVERSE", k
                break
            if low[k] < ref_lo:
                fate, end_i = "RESUME", k
                break
            if (not in_box) and zd <= close[k] <= zg:
                fate, end_i = "REENTRY", k
                break
    return {
        "event_id": ev["event_id"],
        "kind": kind,
        "T_1_VISIBLE": ev["T_1_VISIBLE"],
        "T_FATE": _ts(bar, end_i),
        "in_box_at_t1": in_box,
        "fate": fate,
        "hours_to_fate": round((end_i - i0) * 0.25, 4),  # latency, not duration
    }
