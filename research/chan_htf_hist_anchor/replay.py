"""Causal leftover HTF anchors. Living box excluded. No HTF BSP. No B2."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from chan_fractal_of.clock import resample_bars
from chan_htf_hist_anchor.phase0_schema import assert_no_htf_bsp, is_historical, rail_side
from chan_htf_zs_ltf_b1.replay import bars_to_df, replay_ltf_b1_lock
from chanlun.pipeline.timeframe import TF_DF


@dataclass
class HistBook:
    snaps: list[tuple[pd.Timestamp, dict]]
    birth: dict
    birth_zgzd: dict
    complete: dict
    complete_ggdd: dict


def replay_htf_hist(bar_1h: pd.DataFrame) -> HistBook:
    df = bars_to_df(bar_1h)
    tf = TF_DF()
    tf.init_stream(df.iloc[:1], interval=1, timeframe="1h")
    snaps: list[tuple[pd.Timestamp, dict]] = []
    birth: dict = {}
    birth_zgzd: dict = {}
    complete: dict = {}
    complete_ggdd: dict = {}

    def capture(i: int) -> None:
        close_ts = pd.Timestamp(bar_1h.iloc[i]["close_ts"])
        if close_ts.tzinfo is None:
            close_ts = close_ts.tz_localize("UTC")
        zs_map = {}
        for zs in tf.bi_zs_list:
            zid = zs.start_bi.start_time
            rec = {
                "zg": float(zs.zg),
                "zd": float(zs.zd),
                "gg": float(zs.gg),
                "dd": float(zs.dd),
                "n_bis": int(len(zs.bi_list)),
                "has_next": getattr(zs, "next", None) is not None,
            }
            zs_map[zid] = rec
            if zid not in birth:
                birth[zid] = close_ts
                birth_zgzd[zid] = (rec["zg"], rec["zd"])
            if rec["has_next"] and zid not in complete:
                complete[zid] = close_ts
                complete_ggdd[zid] = (rec["gg"], rec["dd"])
        snaps.append((close_ts, zs_map))
        if tf.bsp_list:
            raise RuntimeError("HTF path emitted bsp_list")

    capture(0)
    print(f"HTF stream 1/{len(df)}", flush=True)
    for i in range(1, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 200 == 0 or i + 1 == len(df):
            print(
                f"HTF stream {i + 1}/{len(df)} born={len(birth)} complete={len(complete)}",
                flush=True,
            )
    return HistBook(snaps, birth, birth_zgzd, complete, complete_ggdd)


def _htf_at(book: HistBook, t_b1: pd.Timestamp) -> dict:
    zs_map = {}
    for close_ts, m in book.snaps:
        if close_ts < t_b1:
            zs_map = m
        else:
            break
    return zs_map


def leftover_at(book: HistBook, t: pd.Timestamp) -> list[dict]:
    t = pd.Timestamp(t)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    zs_map = _htf_at(book, t)
    out = []
    for zid, rec in zs_map.items():
        t_complete = book.complete.get(zid)
        if not is_historical(has_next=rec["has_next"], t_complete=t_complete, t_b1=t):
            continue
        if zid not in book.birth_zgzd or zid not in book.complete_ggdd:
            continue
        zg0, zd0 = book.birth_zgzd[zid]
        gg0, dd0 = book.complete_ggdd[zid]
        item = dict(rec)
        item["zs_id"] = zid
        item["T_ZS_COMPLETE"] = t_complete
        item["zg_ok"] = rec["zg"] == zg0
        item["zd_ok"] = rec["zd"] == zd0
        item["gg_ok"] = rec["gg"] == gg0
        item["dd_ok"] = rec["dd"] == dd0
        out.append(item)
    return out


def attach_hist(ltf_rows: list[dict], book: HistBook) -> list[dict]:
    rows = []
    for b1 in ltf_rows:
        t_b1 = pd.Timestamp(b1["T_LTF_B1"])
        if t_b1.tzinfo is None:
            t_b1 = t_b1.tz_localize("UTC")
        zs_map = _htf_at(book, t_b1)
        hist = []
        for zid, rec in zs_map.items():
            t_complete = book.complete.get(zid)
            if not is_historical(has_next=rec["has_next"], t_complete=t_complete, t_b1=t_b1):
                continue
            zg0, zd0 = book.birth_zgzd[zid]
            gg0, dd0 = book.complete_ggdd[zid]
            t_vis = book.birth[zid]
            zg_ok = rec["zg"] == zg0
            zd_ok = rec["zd"] == zd0
            gg_ok = rec["gg"] == gg0
            dd_ok = rec["dd"] == dd0
            low, high = float(b1["leave_low"]), float(b1["leave_high"])
            item = {
                "LTF_B1": b1["LTF_B1"],
                "T_LTF_B1": t_b1,
                "B1_bar": b1.get("B1_bar"),
                "leave_low": low,
                "leave_high": high,
                "zs_id": zid,
                "T_ZG": t_vis,
                "T_ZD": t_vis,
                "T_ZS_COMPLETE": t_complete,
                "T_GG": t_complete,
                "T_DD": t_complete,
                "zg": rec["zg"] if zg_ok else None,
                "zd": rec["zd"] if zd_ok else None,
                "gg": rec["gg"] if gg_ok else None,
                "dd": rec["dd"] if dd_ok else None,
                "zg_unchanged": zg_ok,
                "zd_unchanged": zd_ok,
                "gg_unchanged": gg_ok,
                "dd_unchanged": dd_ok,
                "side_zg": rail_side(low, high, rec["zg"]) if zg_ok else None,
                "side_zd": rail_side(low, high, rec["zd"]) if zd_ok else None,
                "side_gg": rail_side(low, high, rec["gg"]) if gg_ok else None,
                "side_dd": rail_side(low, high, rec["dd"]) if dd_ok else None,
                "NO_HIST_ANCHOR": False,
                "n_hist_zs": None,
            }
            assert_no_htf_bsp(item)
            hist.append(item)
        if not hist:
            row = {
                "LTF_B1": b1["LTF_B1"],
                "T_LTF_B1": t_b1,
                "B1_bar": b1.get("B1_bar"),
                "leave_low": b1["leave_low"],
                "leave_high": b1["leave_high"],
                "zs_id": None,
                "T_ZG": None,
                "T_ZD": None,
                "T_ZS_COMPLETE": None,
                "T_GG": None,
                "T_DD": None,
                "zg": None,
                "zd": None,
                "gg": None,
                "dd": None,
                "zg_unchanged": None,
                "zd_unchanged": None,
                "gg_unchanged": None,
                "dd_unchanged": None,
                "side_zg": None,
                "side_zd": None,
                "side_gg": None,
                "side_dd": None,
                "NO_HIST_ANCHOR": True,
                "n_hist_zs": 0,
            }
            assert_no_htf_bsp(row)
            rows.append(row)
        else:
            for item in hist:
                item["n_hist_zs"] = len(hist)
                rows.append(item)
    return rows


def build_phase0(kline_1m: pd.DataFrame, ltf_rows: list[dict] | None = None) -> list[dict]:
    bar_1h = resample_bars(kline_1m, 60)
    book = replay_htf_hist(bar_1h)
    if ltf_rows is None:
        bar_15m = resample_bars(kline_1m, 15)
        ltf_rows = replay_ltf_b1_lock(bar_15m)
    return attach_hist(ltf_rows, book)
