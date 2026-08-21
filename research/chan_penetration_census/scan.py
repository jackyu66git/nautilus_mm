"""B1/B2/B3 reverse excursion vs frozen anchors. No ATR. No fate race."""
from __future__ import annotations

import pandas as pd

from chan_2nd_point_fate.detect import classify_second, find_bi, first_leave, zid_of
from chan_3rd_point.detect import classify_pullback
from chan_fractal_of.labels import find_all_bsp_nonesafe
from chan_htf_zs_ltf_b1.replay import WARM, bars_to_df
from chanlun.core.ChanEnum import Chan_BSP_TYPE
from chanlun.pipeline.timeframe import TF_DF

_FIRST = {Chan_BSP_TYPE.B1: "B1", Chan_BSP_TYPE.S1: "S1"}
BUY = {"B1", "B2", "B3"}
BAR_H = 0.25


def scan_anchors(bar_15m: pd.DataFrame) -> dict:
    """One 15m stream. B1/B2/B3 freeze copied from existing scans. Adds leave extremes for B3."""
    df = bars_to_df(bar_15m)
    start = min(WARM, len(df))
    tf = TF_DF()
    tf.init_stream(df.iloc[:start], interval=1, timeframe="15m")
    seen_1: set[tuple] = set()
    leave_2: dict[str, dict] = {}
    class_2: dict[str, dict] = {}
    leave_3: dict[str, dict] = {}
    class_3: dict[str, dict] = {}
    events: list[dict] = []

    def _rec(i: int, eid: str, kind: str, zg: float, zd: float, leave_low: float, leave_high: float) -> None:
        events.append(
            {
                "event_id": eid,
                "kind": kind,
                "zg": zg,
                "zd": zd,
                "leave_low": leave_low,
                "leave_high": leave_high,
                "tape_row": i,
            }
        )

    def capture(i: int) -> None:
        for bsp in find_all_bsp_nonesafe(tf):
            kind = _FIRST.get(bsp.type)
            if kind is None:
                continue
            leave, zs = bsp.bi, bsp.zs
            members = {str(b.start_time) for b in zs.bi_list}
            if str(leave.start_time) in members:
                continue
            key = (str(zs.start_bi.start_time), str(leave.start_time), kind)
            if key in seen_1:
                continue
            seen_1.add(key)
            _rec(
                i,
                f"{zs.start_bi.start_time}:{kind}:{leave.start_time}",
                kind,
                float(zs.zg),
                float(zs.zd),
                float(leave.low),
                float(leave.high),
            )

        for zs in tf.bi_zs_list:
            zid = zid_of(zs)
            if zs.zg is None or zs.zd is None or len(zs.bi_list) < 3:
                continue
            if zid not in class_2 and zid not in leave_2:
                left = first_leave(zs)
                if left is not None:
                    leave, side = left
                    leave_2[zid] = {
                        "side": side,
                        "leave_id": str(leave.start_time),
                        "zg": float(zs.zg),
                        "zd": float(zs.zd),
                        "leave_low": float(leave.low),
                        "leave_high": float(leave.high),
                    }
            if zid not in class_3 and zid not in leave_3:
                left = first_leave(zs)
                if left is not None:
                    leave, side = left
                    leave_3[zid] = {
                        "side": side,
                        "leave_id": str(leave.start_time),
                        "zg": float(zs.zg),
                        "zd": float(zs.zd),
                        "leave_low": float(leave.low),
                        "leave_high": float(leave.high),
                    }

        for zid, rec in list(leave_2.items()):
            if zid in class_2:
                continue
            leave = find_bi(tf, rec["leave_id"])
            if leave is None:
                class_2[zid] = {"kind": "DROP"}
                continue
            zs = next((z for z in tf.bi_zs_list if zid_of(z) == zid), None)
            if zs is None:
                continue
            hit = classify_second(tf, zs, leave, rec["side"])
            if hit is None:
                continue
            class_2[zid] = hit
            if hit["kind"] in ("B2", "S2"):
                _rec(
                    i,
                    f"{zid}:{hit['kind']}:{rec['leave_id']}",
                    hit["kind"],
                    rec["zg"],
                    rec["zd"],
                    rec["leave_low"],
                    rec["leave_high"],
                )

        for zid, rec in list(leave_3.items()):
            if zid in class_3:
                continue
            leave = find_bi(tf, rec["leave_id"])
            if leave is None:
                class_3[zid] = {"kind": "DROP"}
                continue
            hit = classify_pullback(leave, rec["zg"], rec["zd"], rec["side"])
            if hit is None:
                continue
            class_3[zid] = hit
            if hit["kind"] in ("B3", "S3"):
                _rec(
                    i,
                    f"{zid}:{hit['kind']}:{rec['leave_id']}",
                    hit["kind"],
                    rec["zg"],
                    rec["zd"],
                    rec["leave_low"],
                    rec["leave_high"],
                )

    capture(start - 1)
    print(f"pen stream {start}/{len(df)}", flush=True)
    for i in range(start, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(f"pen stream {i + 1}/{len(df)} n={len(events)}", flush=True)
        if tf.bsp_list:
            raise RuntimeError("LTF emitted bsp_list")
    return {"n_15m": len(bar_15m), "events": events}


def _first(n: int, i0: int, pred) -> int | None:
    for k in range(i0 + 1, n):
        if pred(k):
            return k
    return None


def _hours(i0: int, k: int | None) -> float | None:
    if k is None:
        return None
    return round((k - i0) * BAR_H, 4)


def follow_penetration(ev: dict, bar: pd.DataFrame) -> dict:
    i0 = int(ev["tape_row"])
    n = len(bar)
    kind = ev["kind"]
    buy = kind in BUY
    close = bar["close"].to_numpy(float)
    high = bar["high"].to_numpy(float)
    low = bar["low"].to_numpy(float)
    t0_close = float(close[i0])
    t0_high = float(high[i0])
    t0_low = float(low[i0])
    zg, zd = float(ev["zg"]), float(ev["zd"])
    leave_low, leave_high = float(ev["leave_low"]), float(ev["leave_high"])
    box_w = zg - zd
    leave_w = leave_high - leave_low
    t0_in_box = zd <= t0_close <= zg
    t0_overlap_box = not (t0_high < zd or t0_low > zg)
    t0_overlap_leave = not (t0_high < leave_low or t0_low > leave_high)
    hours_available = round((n - 1 - i0) * BAR_H, 4)

    if i0 + 1 >= n:
        min_low = max_high = None
        mae_close = mae_bar = 0.0
        hours_to_mae = None
        i_leave_ext = i_leave_c = i_box_ext = i_box_c = i_far_ext = i_far_c = i_leave_rng = None
    elif buy:
        sl = slice(i0 + 1, n)
        min_i = i0 + 1 + int(low[sl].argmin())
        min_low = float(low[min_i])
        max_high = float(high[sl].max())
        mae_close = max(0.0, t0_close - min_low)
        mae_bar = max(0.0, t0_low - min_low)
        hours_to_mae = _hours(i0, min_i)
        i_leave_ext = _first(n, i0, lambda k: low[k] < leave_low)
        i_leave_c = _first(n, i0, lambda k: close[k] < leave_low)
        i_box_ext = _first(n, i0, lambda k: low[k] <= zg and high[k] >= zd)
        i_box_c = _first(n, i0, lambda k: zd <= close[k] <= zg)
        i_far_ext = _first(n, i0, lambda k: low[k] < zd)
        i_far_c = _first(n, i0, lambda k: close[k] < zd)
        i_leave_rng = None if t0_overlap_leave else _first(
            n, i0, lambda k: not (high[k] < leave_low or low[k] > leave_high)
        )
    else:
        sl = slice(i0 + 1, n)
        max_i = i0 + 1 + int(high[sl].argmax())
        max_high = float(high[max_i])
        min_low = float(low[sl].min())
        mae_close = max(0.0, max_high - t0_close)
        mae_bar = max(0.0, max_high - t0_high)
        hours_to_mae = _hours(i0, max_i)
        i_leave_ext = _first(n, i0, lambda k: high[k] > leave_high)
        i_leave_c = _first(n, i0, lambda k: close[k] > leave_high)
        i_box_ext = _first(n, i0, lambda k: low[k] <= zg and high[k] >= zd)
        i_box_c = _first(n, i0, lambda k: zd <= close[k] <= zg)
        i_far_ext = _first(n, i0, lambda k: high[k] > zg)
        i_far_c = _first(n, i0, lambda k: close[k] > zg)
        i_leave_rng = None if t0_overlap_leave else _first(
            n, i0, lambda k: not (high[k] < leave_low or low[k] > leave_high)
        )

    family = {"B1": "B1", "S1": "B1", "B2": "B2", "S2": "B2", "B3": "B3", "S3": "B3"}[kind]
    pierce_leave = i_leave_ext is not None
    enter_box = i_box_ext is not None
    through_far = i_far_ext is not None
    if family in ("B1", "B2"):
        if mae_bar <= 0:
            layer = "NONE"
        elif not pierce_leave:
            layer = "SHALLOW"
        else:
            layer = "PRIMARY"
    elif mae_bar <= 0:
        layer = "NONE"
    elif not enter_box:
        layer = "SHALLOW"
    elif not through_far:
        layer = "BOX"
    else:
        layer = "THROUGH"

    def _ratio(num: float, den: float) -> float | None:
        if den <= 0:
            return None
        return round(num / den, 6)

    return {
        "event_id": ev["event_id"],
        "kind": kind,
        "family": family,
        "tape_row": i0,
        "zg": zg,
        "zd": zd,
        "leave_low": leave_low,
        "leave_high": leave_high,
        "box_w": round(box_w, 4),
        "leave_w": round(leave_w, 4),
        "t0_close": t0_close,
        "t0_high": t0_high,
        "t0_low": t0_low,
        "t0_in_box": t0_in_box,
        "t0_overlap_box": t0_overlap_box,
        "t0_overlap_leave": t0_overlap_leave,
        "hours_available": hours_available,
        "min_low_after": min_low,
        "max_high_after": max_high,
        "mae_close": round(mae_close, 4),
        "mae_bar": round(mae_bar, 4),
        "mae_over_box": _ratio(mae_close, box_w),
        "mae_over_leave": _ratio(mae_close, leave_w),
        "hours_to_mae": hours_to_mae,
        "pierce_leave_ext": pierce_leave,
        "hours_to_pierce_leave_ext": _hours(i0, i_leave_ext),
        "pierce_leave_close": i_leave_c is not None,
        "hours_to_pierce_leave_close": _hours(i0, i_leave_c),
        "enter_box_ext": enter_box,
        "hours_to_enter_box_ext": _hours(i0, i_box_ext),
        "enter_box_close": i_box_c is not None,
        "hours_to_enter_box_close": _hours(i0, i_box_c),
        "through_far_ext": through_far,
        "hours_to_through_far_ext": _hours(i0, i_far_ext),
        "through_far_close": i_far_c is not None,
        "hours_to_through_far_close": _hours(i0, i_far_c),
        "enter_leave": i_leave_rng is not None,
        "hours_to_enter_leave": _hours(i0, i_leave_rng),
        "layer": layer,
    }
