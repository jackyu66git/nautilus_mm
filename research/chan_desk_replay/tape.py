"""Causal 15m visible-state tape. No interpretation."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from chan_desk_replay.schema import SMC_STATE, assert_clean
from chan_fractal_of.clock import resample_bars
from chan_fractal_of.of_window import load_of_1m
from chan_fractal_of.labels import find_all_bsp_nonesafe
from chan_htf_hist_anchor.phase0_schema import is_historical, rail_side
from chan_htf_hist_anchor.replay import leftover_at, replay_htf_hist
from chan_htf_zs_ltf_b1.replay import bars_to_df
from chan_trade_of.trades import TradeStore, snapshot_slice
from chanlun.core.ChanEnum import Chan_BSP_TYPE, Chan_FX_TYPE
from chanlun.pipeline.timeframe import TF_DF

WARM = 40
RAILS = ("zg", "zd", "gg", "dd")


def _utc(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        return t.tz_localize("UTC")
    return t.tz_convert("UTC")


def _enum_name(v) -> str | None:
    if v is None:
        return None
    return getattr(v, "name", str(v))


def _living_at(book, t: pd.Timestamp) -> str:
    t = _utc(t)
    zs_map = {}
    for close_ts, m in book.snaps:
        if close_ts < t:
            zs_map = m
        else:
            break
    for zid, rec in zs_map.items():
        t_complete = book.complete.get(zid)
        if not is_historical(has_next=rec["has_next"], t_complete=t_complete, t_b1=t):
            return "FORMING"
    return "none"


def replay_ltf_structure(bar_15m: pd.DataFrame) -> list[dict]:
    df = bars_to_df(bar_15m)
    start = min(WARM, len(df))
    tf = TF_DF()
    tf.init_stream(df.iloc[:start], interval=1, timeframe="15m")
    seen_lock = set()
    out: list[dict] = [{} for _ in range(len(bar_15m))]

    def capture(i: int) -> None:
        close_ts = _utc(bar_15m.iloc[i]["close_ts"])
        bi_dir = None
        bi_sure = None
        if tf.bi_list:
            last = tf.bi_list[-1]
            bi_dir = _enum_name(last.dir)
            bi_sure = bool(last.is_sure)
        fx_side = None
        fx_id = None
        t_fx = None
        if len(tf.klc_list) >= 3:
            for klc in reversed(tf.klc_list[:-1]):
                if klc.pre is None or klc.next is None or klc.next.end_klu is None:
                    continue
                fx = tf.check_fx(klc)
                if fx in (Chan_FX_TYPE.BOTTOM, Chan_FX_TYPE.TOP):
                    fx_side = "BOTTOM" if fx == Chan_FX_TYPE.BOTTOM else "TOP"
                    fx_id = klc.start_time
                    t_fx = close_ts
                    break
        lock = False
        lock_id = None
        for bsp in find_all_bsp_nonesafe(tf):
            if bsp.type != Chan_BSP_TYPE.B1:
                continue
            leave = bsp.bi
            zs = bsp.zs
            member_times = {b.start_time for b in zs.bi_list}
            if leave.start_time in member_times:
                continue
            key = (zs.start_bi.start_time, leave.start_time)
            if key in seen_lock:
                continue
            seen_lock.add(key)
            lock = True
            lock_id = leave.start_time
            break
        out[i] = {
            "ltf_bi_dir": bi_dir,
            "ltf_bi_sure": bi_sure,
            "ltf_fx": fx_side,
            "ltf_fx_id": fx_id,
            "T_FX_VISIBLE": str(t_fx) if t_fx is not None else None,
            "b1_lock": lock,
            "b1_lock_id": lock_id,
        }

    for i in range(start):
        capture(i)
    print(f"LTF structure {start}/{len(df)}", flush=True)
    for i in range(start, len(df)):
        tf.append_bar(df.iloc[i])
        capture(i)
        if i % 400 == 0 or i + 1 == len(df):
            print(f"LTF structure {i + 1}/{len(df)}", flush=True)
    return out


class DailyTrades:
    def __init__(self, root):
        self.root = root
        self._cache: dict[date, TradeStore | None] = {}

    def store_for(self, d: date) -> TradeStore | None:
        if d in self._cache:
            return self._cache[d]
        path = self.root / f"{d.isoformat()}.parquet"
        if not path.exists():
            self._cache[d] = None
            return None
        t = pd.read_parquet(path, columns=["ts", "price", "qty", "is_buyer_maker"])
        t["ts"] = pd.to_datetime(t["ts"], utc=True)
        t = t.dropna(subset=["ts", "price", "qty"]).sort_values("ts")
        ts = t["ts"].dt.tz_localize(None).to_numpy(dtype="datetime64[ns]")
        price = t["price"].to_numpy(dtype=np.float64)
        qty = t["qty"].to_numpy(dtype=np.float64)
        sell = t["is_buyer_maker"].to_numpy(dtype=bool)
        delta = np.where(sell, -qty, qty)
        store = TradeStore(ts, price, qty, delta)
        self._cache[d] = store
        if len(self._cache) > 2:
            keep = {d0 for d0 in self._cache if d0 >= d - timedelta(days=1)}
            self._cache = {k: v for k, v in self._cache.items() if k in keep or k == d}
        return store

    def snap(self, open_ts: pd.Timestamp, close_ts: pd.Timestamp):
        open_ts, close_ts = _utc(open_ts), _utc(close_ts)
        d0, d1 = open_ts.date(), close_ts.date()
        days = [d0] if d0 == d1 else [d0, d1]
        n = vol_delta = 0.0
        hhi = push = speed = 0.0
        n_tr = 0
        loaded = False
        for d in days:
            store = self.store_for(d)
            if store is None:
                continue
            loaded = True
            lo = np.datetime64(open_ts.tz_localize(None), "ns")
            hi = np.datetime64(close_ts.tz_localize(None), "ns")
            i0 = int(np.searchsorted(store.ts, lo, side="left"))
            i1 = int(np.searchsorted(store.ts, hi, side="left"))
            snap = snapshot_slice(store, i0, i1)
            n_tr += snap.n
            vol_delta += snap.delta
            if snap.n:
                hhi = snap.hhi
                push = snap.push
                speed = snap.speed
        if not loaded:
            return None
        return {
            "of_trade_status": "ok",
            "of_trade_n": int(n_tr),
            "of_trade_delta": float(vol_delta),
            "of_hhi": float(hhi),
            "of_push": float(push),
            "of_speed": float(speed),
        }


def _kline_of_bar(of_1m: pd.DataFrame, open_ts, close_ts) -> tuple[float, float]:
    open_ts, close_ts = _utc(open_ts), _utc(close_ts)
    w = of_1m[(of_1m["open_ts"] >= open_ts) & (of_1m["open_ts"] < close_ts)]
    if w.empty:
        return 0.0, 0.0
    return float(w["delta"].sum()), float(w["volume"].sum())


def build_tape(kline_1m: pd.DataFrame, of_1m: pd.DataFrame, agg_daily) -> list[dict]:
    bar_15m = resample_bars(kline_1m, 15)
    bar_1h = resample_bars(kline_1m, 60)
    print(f"bars 15m={len(bar_15m)} 1h={len(bar_1h)}", flush=True)
    book = replay_htf_hist(bar_1h)
    struct = replay_ltf_structure(bar_15m)
    trades = DailyTrades(agg_daily)
    rows = []
    for i in range(len(bar_15m)):
        close_ts = _utc(bar_15m.iloc[i]["close_ts"])
        open_ts = _utc(bar_15m.iloc[i]["open_ts"])
        low = float(bar_15m.iloc[i]["low"])
        high = float(bar_15m.iloc[i]["high"])
        hist = leftover_at(book, close_ts)
        leftover = []
        for h in hist:
            item = {
                "zs_id": h["zs_id"],
                "T_ZS_COMPLETE": str(h["T_ZS_COMPLETE"]),
                "zg": h["zg"] if h.get("zg_ok") else None,
                "zd": h["zd"] if h.get("zd_ok") else None,
                "gg": h["gg"] if h.get("gg_ok") else None,
                "dd": h["dd"] if h.get("dd_ok") else None,
            }
            for rail in RAILS:
                if h.get(f"{rail}_ok"):
                    item[f"side_{rail}"] = rail_side(low, high, h[rail])
                else:
                    item[f"side_{rail}"] = None
            leftover.append(item)
        dlt, vol = _kline_of_bar(of_1m, open_ts, close_ts)
        tr = trades.snap(open_ts, close_ts)
        st = struct[i] if struct[i] else {
            "ltf_bi_dir": None,
            "ltf_bi_sure": None,
            "ltf_fx": None,
            "ltf_fx_id": None,
            "T_FX_VISIBLE": None,
            "b1_lock": False,
            "b1_lock_id": None,
        }
        rec = {
            "t": str(close_ts),
            "open_ts": str(open_ts),
            "htf_anchor_count": len(leftover),
            "htf_leftover": leftover,
            "htf_living": _living_at(book, close_ts),
            "ltf_bi_dir": st.get("ltf_bi_dir"),
            "ltf_bi_sure": st.get("ltf_bi_sure"),
            "ltf_fx": st.get("ltf_fx"),
            "ltf_fx_id": st.get("ltf_fx_id"),
            "T_FX_VISIBLE": st.get("T_FX_VISIBLE"),
            "b1_lock": bool(st.get("b1_lock")),
            "b1_lock_id": st.get("b1_lock_id"),
            "of_kline_delta": dlt,
            "of_kline_volume": vol,
            "of_window_end": str(close_ts),
            "smc_state": SMC_STATE,
        }
        if tr is None:
            rec.update(
                {
                    "of_trade_status": "not_loaded",
                    "of_trade_n": None,
                    "of_trade_delta": None,
                    "of_hhi": None,
                    "of_push": None,
                    "of_speed": None,
                }
            )
        else:
            rec.update(tr)
        if rec.get("T_FX_VISIBLE"):
            t_fx = _utc(rec["T_FX_VISIBLE"])
            if _utc(rec["of_window_end"]) > t_fx:
                rec["of_window_end"] = str(t_fx)
        assert_clean(rec)
        rows.append(rec)
        if (i + 1) % 500 == 0 or i + 1 == len(bar_15m):
            print(f"tape {i + 1}/{len(bar_15m)} leftover={len(leftover)}", flush=True)
    return rows
