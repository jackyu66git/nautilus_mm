"""Stream 15m third-class points. Leave freezes zg/zd; pullback classifies against freeze."""
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


def _hours(a, b) -> float:
    return round(float((pd.Timestamp(b) - pd.Timestamp(a)).total_seconds() / 3600.0), 6)


def scan_third(bar_15m: pd.DataFrame) -> dict:
    df = bars_to_df(bar_15m)
    start = min(WARM, len(df))
    tf = TF_DF()
    tf.init_stream(df.iloc[:start], interval=1, timeframe="15m")
    zs_birth: dict[str, str] = {}
    zs_complete: dict[str, str] = {}
    leave_seen: dict[str, dict] = {}
    classified: dict[str, dict] = {}
    events: list[dict] = []
    n_drop = 0

    def capture(i: int) -> None:
        nonlocal n_drop
        close = str(_ts(bar_15m, i))
        for zs in tf.bi_zs_list:
            zid = zid_of(zs)
            if zid not in zs_birth:
                zs_birth[zid] = close
            if getattr(zs, "next", None) is not None and zid not in zs_complete:
                zs_complete[zid] = close
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
                n_drop += 1
                continue
            hit = classify_pullback(leave, rec["zg"], rec["zd"], rec["side"])
            if hit is None:
                continue
            classified[zid] = hit
            if hit["kind"] not in ("B3", "S3"):
                continue
            t_zs = zs_birth[zid]
            t_leave = rec["T_LEAVE_VISIBLE"]
            events.append(
                {
                    "event_id": f"{zid}:{hit['kind']}:{rec['leave_id']}",
                    "kind": hit["kind"],
                    "zs_id": zid,
                    "T_ZS_VISIBLE": t_zs,
                    "T_ZS_COMPLETE": zs_complete.get(zid),
                    "T_LEAVE_VISIBLE": t_leave,
                    "T_3_VISIBLE": close,
                    "zg": rec["zg"],
                    "zd": rec["zd"],
                    "leave_id": rec["leave_id"],
                    "pullback_id": str(hit["pullback"].start_time),
                    "tape_row": i,
                }
            )

    capture(start - 1)
    print(f"3rd stream {start}/{len(df)}", flush=True)
    for i in range(start, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(
                f"3rd stream {i + 1}/{len(df)} n_3={len(events)} n_leave={len(leave_seen)}",
                flush=True,
            )

    kinds = [c.get("kind") for c in classified.values()]
    waiting = [z for z in leave_seen if z not in classified]
    return {
        "n_15m": len(bar_15m),
        "n_zs": len(zs_birth),
        "n_zs_complete": len(zs_complete),
        "n_leave": len(leave_seen),
        "n_pullback_in": kinds.count("PULLBACK_IN"),
        "n_wrong_dir": kinds.count("WRONG_DIR"),
        "n_drop": n_drop,
        "n_waiting_pb": len(waiting),
        "n_b3": kinds.count("B3"),
        "n_s3": kinds.count("S3"),
        "events": events,
    }


def audit(payload: dict) -> dict:
    events = payload["events"]
    clock_ok = True
    for r in events:
        if not (r["T_ZS_VISIBLE"] <= r["T_LEAVE_VISIBLE"] < r["T_3_VISIBLE"]):
            clock_ok = False
    ids = [r["event_id"] for r in events]
    unique = len(ids) == len(set(ids))
    n3 = len(events)
    if not clock_ok:
        decision, kind = "FAIL", "LEAK"
    elif not unique:
        decision, kind = "FAIL", "CLOCK"
    elif n3 == 0 and payload["n_leave"] == 0:
        decision, kind = "FAIL", "NO_OBJECT"
    elif n3 == 0:
        decision, kind = "FAIL", "NO_THIRD_POINT"
    else:
        decision, kind = "PASS", "CENSUS_OK"
    durs = [_hours(r["T_LEAVE_VISIBLE"], r["T_3_VISIBLE"]) for r in events]
    p50 = sorted(durs)[len(durs) // 2] if durs else None
    return {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "unique": unique,
        "n_zs": payload["n_zs"],
        "n_zs_complete": payload["n_zs_complete"],
        "n_leave": payload["n_leave"],
        "n_pullback_in": payload["n_pullback_in"],
        "n_wrong_dir": payload["n_wrong_dir"],
        "n_drop": payload["n_drop"],
        "n_waiting_pb": payload["n_waiting_pb"],
        "n_b3": payload["n_b3"],
        "n_s3": payload["n_s3"],
        "n_3": n3,
        "leave_to_3_hours_p50": p50,
        "blocked": "无 MFE/OF/SMC/交易。离开时冻结 zg/zd。回抽后再进中枢不用于定义。",
    }
