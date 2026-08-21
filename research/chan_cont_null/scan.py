"""Null control for weak RESUME. Ordinary 15m bars. Not another structure signal."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BUY = {"B1", "B2", "B3"}
SELL = {"S1", "S2", "S3"}
TS_KEY = {"B1": "T_1_VISIBLE", "S1": "T_1_VISIBLE", "B2": "T_2_VISIBLE", "S2": "T_2_VISIBLE", "B3": "T_3_VISIBLE", "S3": "T_3_VISIBLE"}


def _ts(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert("UTC")


def load_events(*paths: Path) -> list[dict]:
    rows = []
    for p in paths:
        for line in p.read_text().splitlines():
            if line:
                rows.append(json.loads(line))
    return rows


def event_index(bar: pd.DataFrame, ev: dict) -> int | None:
    kind = ev["kind"]
    t = _ts(ev[TS_KEY[kind]])
    close = pd.to_datetime(bar["close_ts"], utc=True)
    hit = close == t
    if not hit.any():
        return None
    return int(hit.to_numpy().nonzero()[0][0])


def next_extends(high, low, i: int, side: str) -> bool:
    if i + 1 >= len(high):
        return False
    if side == "BUY":
        return float(high[i + 1]) > float(high[i])
    return float(low[i + 1]) < float(low[i])


def null_rates(high, low, skip: set[int]) -> dict:
    n = len(high) - 1
    up = down = 0
    n_null = 0
    for i in range(n):
        if i in skip:
            continue
        n_null += 1
        if float(high[i + 1]) > float(high[i]):
            up += 1
        if float(low[i + 1]) < float(low[i]):
            down += 1
    return {
        "n_null": n_null,
        "p_up": round(up / n_null, 6) if n_null else None,
        "p_down": round(down / n_null, 6) if n_null else None,
        "n_up": up,
        "n_down": down,
    }
