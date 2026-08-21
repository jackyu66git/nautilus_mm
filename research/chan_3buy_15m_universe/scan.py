"""Independent 3rd-point census per TF. Same detect as CHAN_3RD_POINT_001. No EMA."""
from __future__ import annotations

import pandas as pd

from chan_3rd_point.detect import classify_pullback, find_bi, first_leave, zid_of
from chan_htf_zs_ltf_b1.replay import WARM, bars_to_df
from chanlun.pipeline.timeframe import TF_DF


def _ts(bar, i) -> pd.Timestamp:
    ts = pd.Timestamp(bar.iloc[i]["close_ts"])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts


def scan_third_tf(bar: pd.DataFrame, timeframe: str) -> dict:
    df = bars_to_df(bar)
    start = min(WARM, len(df))
    tf = TF_DF()
    tf.init_stream(df.iloc[:start], interval=1, timeframe=timeframe)
    zs_birth: dict[str, str] = {}
    leave_seen: dict[str, dict] = {}
    classified: dict[str, dict] = {}
    events: list[dict] = []

    def capture(i: int) -> None:
        close = str(_ts(bar, i))
        for zs in tf.bi_zs_list:
            zid = zid_of(zs)
            if zid not in zs_birth:
                zs_birth[zid] = close
            if zid in classified or zid in leave_seen:
                continue
            if zs.zg is None or zs.zd is None or len(zs.bi_list) < 3:
                continue
            left = first_leave(zs)
            if left is None:
                continue
            leave, side = left
            leave_seen[zid] = {
                "T_LEAVE_VISIBLE": close,
                "side": side,
                "leave_id": str(leave.start_time),
                "zg": float(zs.zg),
                "zd": float(zs.zd),
            }
        for zid, rec in list(leave_seen.items()):
            if zid in classified:
                continue
            leave = find_bi(tf, rec["leave_id"])
            if leave is None:
                classified[zid] = {"kind": "DROP"}
                continue
            hit = classify_pullback(leave, rec["zg"], rec["zd"], rec["side"])
            if hit is None:
                continue
            classified[zid] = hit
            if hit["kind"] not in ("B3", "S3"):
                continue
            events.append(
                {
                    "event_id": f"{zid}:{hit['kind']}:{rec['leave_id']}",
                    "kind": hit["kind"],
                    "zs_id": zid,
                    "T_LEAVE_VISIBLE": rec["T_LEAVE_VISIBLE"],
                    "T_3_VISIBLE": close,
                    "tape_row": i,
                    "timeframe": timeframe,
                }
            )

    capture(start - 1)
    print(f"{timeframe} 3rd {start}/{len(df)}", flush=True)
    for i in range(start, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(
                f"{timeframe} 3rd {i + 1}/{len(df)} n_3={len(events)} n_leave={len(leave_seen)}",
                flush=True,
            )
        if tf.bsp_list:
            raise RuntimeError(f"{timeframe} emitted bsp_list")
    kinds = [c.get("kind") for c in classified.values()]
    return {
        "timeframe": timeframe,
        "n_bars": len(bar),
        "n_zs": len(zs_birth),
        "n_leave": len(leave_seen),
        "n_b3": kinds.count("B3"),
        "n_s3": kinds.count("S3"),
        "n_3": len(events),
        "n_pullback_in": kinds.count("PULLBACK_IN"),
        "events": events,
    }
