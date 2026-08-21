"""Stream 15m 2nd points then structural fate. No EMA. No OF."""
from __future__ import annotations

import pandas as pd

from chan_2nd_point_fate.detect import classify_second, find_bi, first_leave, zid_of
from chan_ema52_where.scan import _ts
from chan_htf_zs_ltf_b1.replay import WARM, bars_to_df
from chanlun.pipeline.timeframe import TF_DF


def scan_second(bar_15m: pd.DataFrame) -> dict:
    df = bars_to_df(bar_15m)
    start = min(WARM, len(df))
    tf = TF_DF()
    tf.init_stream(df.iloc[:start], interval=1, timeframe="15m")
    leave_seen: dict[str, dict] = {}
    classified: dict[str, dict] = {}
    events: list[dict] = []

    def capture(i: int) -> None:
        close = str(_ts(bar_15m, i))
        for zs in tf.bi_zs_list:
            zid = zid_of(zs)
            if zid in classified or zid in leave_seen:
                continue
            if zs.zg is None or zs.zd is None or len(zs.bi_list) < 3:
                continue
            left = first_leave(zs)
            if left is None:
                continue
            leave, side = left
            leave_seen[zid] = {
                "side": side,
                "leave_id": str(leave.start_time),
                "zg": float(zs.zg),
                "zd": float(zs.zd),
                "leave_low": float(leave.low),
                "leave_high": float(leave.high),
            }
        for zid, rec in list(leave_seen.items()):
            if zid in classified:
                continue
            leave = find_bi(tf, rec["leave_id"])
            if leave is None:
                classified[zid] = {"kind": "DROP"}
                continue
            zs = None
            for z in tf.bi_zs_list:
                if zid_of(z) == zid:
                    zs = z
                    break
            if zs is None:
                continue
            hit = classify_second(tf, zs, leave, rec["side"])
            if hit is None:
                continue
            classified[zid] = hit
            if hit["kind"] not in ("B2", "S2"):
                continue
            px = float(bar_15m.iloc[i]["close"])
            in_box = rec["zd"] <= px <= rec["zg"]
            events.append(
                {
                    "event_id": f"{zid}:{hit['kind']}:{rec['leave_id']}",
                    "kind": hit["kind"],
                    "zs_id": zid,
                    "T_2_VISIBLE": close,
                    "zg": rec["zg"],
                    "zd": rec["zd"],
                    "leave_low": rec["leave_low"],
                    "leave_high": rec["leave_high"],
                    "in_box_at_t2": in_box,
                    "tape_row": i,
                }
            )

    capture(start - 1)
    print(f"2nd stream {start}/{len(df)}", flush=True)
    for i in range(start, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(
                f"2nd stream {i + 1}/{len(df)} n_2={len(events)} n_leave={len(leave_seen)}",
                flush=True,
            )
        if tf.bsp_list:
            raise RuntimeError("LTF emitted bsp_list")
    kinds = [c.get("kind") for c in classified.values()]
    return {
        "n_15m": len(bar_15m),
        "n_leave": len(leave_seen),
        "n_b2": kinds.count("B2"),
        "n_s2": kinds.count("S2"),
        "n_no_first": kinds.count("NO_FIRST"),
        "n_broke_first": kinds.count("BROKE_FIRST"),
        "events": events,
    }


def follow_fate(ev: dict, bar: pd.DataFrame) -> dict:
    i0 = int(ev["tape_row"])
    n = len(bar)
    close = bar["close"].to_numpy(float)
    high = bar["high"].to_numpy(float)
    low = bar["low"].to_numpy(float)
    zg, zd = float(ev["zg"]), float(ev["zd"])
    leave_low, leave_high = float(ev["leave_low"]), float(ev["leave_high"])
    kind = ev["kind"]
    in_box = bool(ev["in_box_at_t2"])
    ref_hi, ref_lo = float(high[i0]), float(low[i0])
    fate = "CENSOR"
    end_i = n - 1
    for k in range(i0 + 1, n):
        if kind == "B2":
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
        "T_2_VISIBLE": ev["T_2_VISIBLE"],
        "T_FATE": _ts(bar, end_i),
        "in_box_at_t2": in_box,
        "fate": fate,
        "hours_to_fate": round((end_i - i0) * 0.25, 4),  # latency, not duration
    }
