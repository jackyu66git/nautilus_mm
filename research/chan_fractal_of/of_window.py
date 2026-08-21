"""Causal OF on 1m. t < T_FX_VISIBLE only."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from chan_fractal_of.clock import FractalEvent


@dataclass
class OfSnapshot:
    n_1m: int
    of_volume: float
    of_taker_buy: float
    of_taker_sell: float
    of_delta: float
    of_imbalance: float
    future_leak: int


def load_of_1m(path) -> pd.DataFrame:
    of = pd.read_parquet(path)
    of["open_ts"] = pd.to_datetime(of["open_ts"], utc=True)
    of["taker_buy_base"] = pd.to_numeric(of["taker_buy_base"], errors="coerce")
    of["volume"] = pd.to_numeric(of["volume"], errors="coerce")
    of["delta"] = 2.0 * of["taker_buy_base"] - of["volume"]
    of["taker_sell"] = of["volume"] - of["taker_buy_base"]
    return of.sort_values("open_ts").reset_index(drop=True)


def _clip(of: pd.DataFrame, start: pd.Timestamp | None, end: pd.Timestamp | None, t_vis: pd.Timestamp) -> pd.DataFrame:
    if start is None or end is None:
        return of.iloc[0:0]
    t_vis = pd.Timestamp(t_vis)
    if t_vis.tzinfo is None:
        t_vis = t_vis.tz_localize("UTC")
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    w = of[(of["open_ts"] >= start) & (of["open_ts"] < end) & (of["open_ts"] < t_vis)]
    return w


def _snap(w: pd.DataFrame, of: pd.DataFrame, t_vis: pd.Timestamp) -> OfSnapshot:
    t_vis = pd.Timestamp(t_vis)
    if t_vis.tzinfo is None:
        t_vis = t_vis.tz_localize("UTC")
    leak = int((w["open_ts"] >= t_vis).sum()) if len(w) else 0
    if leak:
        w = w[w["open_ts"] < t_vis]
    if w.empty:
        return OfSnapshot(0, 0.0, 0.0, 0.0, 0.0, 0.0, leak)
    vol = float(w["volume"].sum())
    buy = float(w["taker_buy_base"].sum())
    sell = float(w["taker_sell"].sum())
    delta = float(w["delta"].sum())
    den = buy + sell
    imb = float((buy - sell) / den) if den else 0.0
    return OfSnapshot(len(w), vol, buy, sell, delta, imb, leak)


def snapshots_for_event(event: FractalEvent, of: pd.DataFrame) -> dict[str, OfSnapshot]:
    t = event.T_FX_VISIBLE
    forming = _snap(_clip(of, event.left_start, event.mid_end, t), of, t)
    candidate = _snap(_clip(of, event.left_start, event.right_end, t), of, t)
    # visible = same causal window as candidate (right span clipped by t < T_vis)
    visible = candidate
    return {"forming": forming, "candidate": candidate, "visible": visible}
