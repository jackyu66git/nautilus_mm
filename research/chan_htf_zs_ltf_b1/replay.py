"""Causal HTF 1H zs snapshots + LTF 15m B1_LOCK. No HTF BSP. No B2 rate."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from chan_fractal_of.clock import resample_bars
from chan_fractal_of.labels import find_all_bsp_nonesafe
from chan_htf_zs_ltf_b1.frozen_config import assert_clean
from chan_htf_zs_ltf_b1.phase0_schema import living_at_b1, spatial_bucket
from chanlun.core.ChanEnum import Chan_BSP_TYPE
from chanlun.pipeline.timeframe import TF_DF

WARM = 40


def bars_to_df(bar: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(bar["open_ts"], utc=True).dt.tz_convert("UTC").dt.tz_localize(None),
            "open": bar["open"].astype(float),
            "high": bar["high"].astype(float),
            "low": bar["low"].astype(float),
            "close": bar["close"].astype(float),
            "volume": bar["volume"].astype(float),
        }
    )


def _close_ts(bar: pd.DataFrame, i: int) -> pd.Timestamp:
    ts = pd.Timestamp(bar.iloc[i]["close_ts"])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts


@dataclass
class HtfBook:
    snaps: list[tuple[pd.Timestamp, dict]]
    birth: dict
    birth_zgzd: dict


def replay_htf_zs(bar_1h: pd.DataFrame) -> HtfBook:
    df = bars_to_df(bar_1h)
    tf = TF_DF()
    tf.init_stream(df.iloc[:1], interval=1, timeframe="1h")
    snaps: list[tuple[pd.Timestamp, dict]] = []
    birth: dict = {}
    birth_zgzd: dict = {}

    def capture(i: int) -> None:
        close_ts = _close_ts(bar_1h, i)
        zs_map = {}
        for zs in tf.bi_zs_list:
            zid = zs.start_bi.start_time
            rec = {
                "zg": float(zs.zg),
                "zd": float(zs.zd),
                "n_bis": int(len(zs.bi_list)),
                "has_next": getattr(zs, "next", None) is not None,
                "is_sure": bool(zs.is_sure),
            }
            zs_map[zid] = rec
            if zid not in birth:
                birth[zid] = close_ts
                birth_zgzd[zid] = (rec["zg"], rec["zd"], rec["n_bis"])
        snaps.append((close_ts, zs_map))

    capture(0)
    print(f"HTF stream 1/{len(df)}", flush=True)
    for i in range(1, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 200 == 0 or i + 1 == len(df):
            print(f"HTF stream {i + 1}/{len(df)} zs={len(birth)}", flush=True)
        if tf.bsp_list:
            raise RuntimeError("HTF path emitted bsp_list")
    return HtfBook(snaps=snaps, birth=birth, birth_zgzd=birth_zgzd)


def replay_ltf_b1_lock(bar_15m: pd.DataFrame) -> list[dict]:
    df = bars_to_df(bar_15m)
    start = min(WARM, len(df))
    tf = TF_DF()
    tf.init_stream(df.iloc[:start], interval=1, timeframe="15m")
    seen = set()
    out = []

    def scan(i: int) -> None:
        close_ts = _close_ts(bar_15m, i)
        for bsp in find_all_bsp_nonesafe(tf):
            if bsp.type != Chan_BSP_TYPE.B1:
                continue
            leave = bsp.bi
            zs = bsp.zs
            member_times = {b.start_time for b in zs.bi_list}
            if leave.start_time in member_times:
                continue
            key = (zs.start_bi.start_time, leave.start_time)
            if key in seen:
                continue
            seen.add(key)
            rec = {
                "LTF_B1": leave.start_time,
                "T_LTF_B1": close_ts,
                "B1_bar": str(bar_15m.iloc[i]["open_ts"]),
                "leave_low": float(leave.end_klc.low),
                "leave_high": float(leave.end_klc.high),
                "ltf_zs_id": zs.start_bi.start_time,
            }
            assert_clean(rec)
            out.append(rec)

    scan(start - 1)
    print(f"LTF B1_LOCK stream {start}/{len(df)}", flush=True)
    for i in range(start, len(df)):
        tf.append_bar(df.iloc[i])
        scan(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(f"LTF B1_LOCK stream {i + 1}/{len(df)} n_lock={len(out)}", flush=True)
    return out


def _htf_at(book: HtfBook, t_b1: pd.Timestamp) -> tuple[pd.Timestamp | None, dict]:
    chosen = None
    zs_map = {}
    for close_ts, m in book.snaps:
        if close_ts < t_b1:
            chosen = close_ts
            zs_map = m
        else:
            break
    return chosen, zs_map


def _pos(low: float, zd: float, zg: float) -> float:
    width = zg - zd
    if width <= 0:
        return float("nan")
    return (low - zd) / width


def _dist_unit(pos: float) -> float:
    if pos < 0:
        return -pos
    if pos > 1:
        return pos - 1
    return 0.0


def attach_htf(ltf_rows: list[dict], book: HtfBook) -> list[dict]:
    rows = []
    for b1 in ltf_rows:
        t_b1 = pd.Timestamp(b1["T_LTF_B1"])
        _, zs_map = _htf_at(book, t_b1)
        candidates = []
        leftover = []
        n_rewrite = 0
        for zid, rec in zs_map.items():
            vis = book.birth[zid]
            zg0, zd0, n0 = book.birth_zgzd[zid]
            unchanged = rec["zg"] == zg0 and rec["zd"] == zd0
            if not unchanged:
                n_rewrite += 1
            present = True
            living = living_at_b1(present=present, has_next=rec["has_next"], zg_zd_unchanged=unchanged)
            item = {
                "zs_id": zid,
                "T_HTF_ZS_VISIBLE": vis,
                "ZS_birth_bar": str(vis),
                "zg_at_visibility": zg0,
                "zd_at_visibility": zd0,
                "zg_at_B1": rec["zg"],
                "zd_at_B1": rec["zd"],
                "zs_present_at_b1": True,
                "zs_living_at_b1": (not rec["has_next"]) and unchanged,
                "zs_leftover_at_b1": rec["has_next"] and unchanged,
                "zg_zd_unchanged": unchanged,
                "ZS_EXPAND": rec["n_bis"] > n0,
                "ZS_valid_at_B1": living,
                "delta_t": (t_b1 - vis).total_seconds() if vis < t_b1 else None,
            }
            if living and vis < t_b1:
                pos = _pos(b1["leave_low"], rec["zd"], rec["zg"])
                item["pos"] = pos
                item["_dist"] = _dist_unit(pos) if pos == pos else 1e9
                candidates.append(item)
            elif rec["has_next"] and unchanged and vis < t_b1:
                leftover.append(item)
        row = dict(b1)
        row["n_htf_rewrite_at_b1"] = n_rewrite
        if not candidates:
            row.update(
                {
                    "NO_HTF_ZS": True,
                    "ZS_valid_at_B1": False,
                    "spatial_bucket": None,
                    "T_HTF_ZS_VISIBLE": None,
                    "delta_t": None,
                    "zs_id": leftover[0]["zs_id"] if leftover else None,
                    "zs_leftover_at_b1": bool(leftover),
                    "zs_present_at_b1": bool(zs_map),
                    "zs_living_at_b1": False,
                    "zg_zd_unchanged": None,
                    "ZS_EXPAND": None,
                    "zg_at_visibility": None,
                    "zd_at_visibility": None,
                    "zg_at_B1": None,
                    "zd_at_B1": None,
                    "ZS_birth_bar": None,
                    "pos": None,
                }
            )
        else:
            candidates.sort(key=lambda x: (x["_dist"], x["T_HTF_ZS_VISIBLE"]))
            main = candidates[0]
            main.pop("_dist", None)
            row.update(main)
            row["NO_HTF_ZS"] = False
            row["spatial_bucket"] = spatial_bucket(
                b1["leave_low"], b1["leave_high"], main["zd_at_B1"], main["zg_at_B1"]
            )
        assert_clean(row)
        rows.append(row)
    return rows


def build_phase0(kline_1m: pd.DataFrame) -> list[dict]:
    bar_15m = resample_bars(kline_1m, 15)
    bar_1h = resample_bars(kline_1m, 60)
    book = replay_htf_zs(bar_1h)
    ltf = replay_ltf_b1_lock(bar_15m)
    return attach_htf(ltf, book)
