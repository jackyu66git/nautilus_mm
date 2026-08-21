"""Causal aggTrades window. t < T_FX_VISIBLE only. No absorption flag."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from chan_trade_of.frozen_config import TICK
from chan_trade_of.paths import AGG_DAILY


@dataclass
class TradeStore:
    ts: np.ndarray
    price: np.ndarray
    qty: np.ndarray
    delta: np.ndarray


def load_trade_store(path: Path | None = None) -> TradeStore:
    root = Path(path or AGG_DAILY)
    files = sorted(root.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no aggTrades parquet in {root}")
    parts = [pd.read_parquet(f, columns=["ts", "price", "qty", "is_buyer_maker"]) for f in files]
    t = pd.concat(parts, ignore_index=True)
    t["ts"] = pd.to_datetime(t["ts"], utc=True)
    t = t.dropna(subset=["ts", "price", "qty"]).sort_values("ts")
    ts = t["ts"].to_numpy(dtype="datetime64[ns]")
    price = t["price"].to_numpy(dtype=np.float64)
    qty = t["qty"].to_numpy(dtype=np.float64)
    sell = t["is_buyer_maker"].to_numpy(dtype=bool)
    delta = np.where(sell, -qty, qty)
    return TradeStore(ts, price, qty, delta)


def _ns(x) -> np.datetime64:
    t = pd.Timestamp(x)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    return np.datetime64(t.tz_localize(None), "ns")


def clip_index(store: TradeStore, start, end, t_vis) -> tuple[int, int]:
    if start is None or end is None:
        return 0, 0
    lo = _ns(start)
    hi = min(_ns(end), _ns(t_vis))
    i0 = int(np.searchsorted(store.ts, lo, side="left"))
    i1 = int(np.searchsorted(store.ts, hi, side="left"))
    return i0, i1


def clip_trades(trades: pd.DataFrame, start, end, t_vis) -> pd.DataFrame:
    if start is None or end is None:
        return trades.iloc[0:0]
    t_vis = pd.Timestamp(t_vis)
    if t_vis.tzinfo is None:
        t_vis = t_vis.tz_localize("UTC")
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    ts = pd.to_datetime(trades["ts"], utc=True)
    return trades[(ts >= start) & (ts < end) & (ts < t_vis)]


@dataclass
class TradeSnap:
    n: int
    volume: float
    delta: float
    duration_s: float
    hhi: float
    n_levels: int
    speed: float
    push: float
    leak: int


def _hhi(price: np.ndarray, qty: np.ndarray) -> tuple[float, int]:
    if len(qty) == 0:
        return 0.0, 0
    tick = np.round(price / TICK) * TICK
    uniq, inv = np.unique(tick, return_inverse=True)
    vol = np.bincount(inv, weights=qty)
    tot = float(vol.sum())
    if tot <= 0:
        return 0.0, int(len(uniq))
    p = vol / tot
    return float(np.sum(p * p)), int(len(uniq))


def snapshot_slice(store: TradeStore, i0: int, i1: int) -> TradeSnap:
    if i1 <= i0:
        return TradeSnap(0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, 0)
    price = store.price[i0:i1]
    qty = store.qty[i0:i1]
    delta = float(store.delta[i0:i1].sum())
    vol = float(qty.sum())
    dur = max((store.ts[i1 - 1] - store.ts[i0]) / np.timedelta64(1, "s"), 1.0)
    hhi, nlev = _hhi(price, qty)
    push = float(abs(price[-1] - price[0]) / max(abs(delta), 1e-9))
    return TradeSnap(i1 - i0, vol, delta, float(dur), hhi, nlev, float((i1 - i0) / dur), push, 0)


def forming_snap(event, store: TradeStore) -> TradeSnap:
    i0, i1 = clip_index(store, event.left_start, event.mid_end, event.T_FX_VISIBLE)
    return snapshot_slice(store, i0, i1)
