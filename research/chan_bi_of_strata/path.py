"""Path stats after T_BI_SURE. Long bottoms / short tops. 16-bar window."""
from __future__ import annotations

import numpy as np
import pandas as pd

from chan_bi_of_strata.frozen_config import FEE_RT, HOLDS


def align_entry(bar: pd.DataFrame, t_sure: pd.Timestamp) -> int | None:
    close_ts = pd.to_datetime(bar["close_ts"], utc=True)
    t_sure = pd.Timestamp(t_sure)
    if t_sure.tzinfo is None:
        t_sure = t_sure.tz_localize("UTC")
    else:
        t_sure = t_sure.tz_convert("UTC")
    hits = np.flatnonzero((close_ts >= t_sure).to_numpy())
    if len(hits) == 0:
        return None
    return int(hits[0])


def path_stats(bar: pd.DataFrame, entry_i: int, side: str) -> dict | None:
    max_h = max(HOLDS)
    if entry_i + max_h >= len(bar):
        return None
    entry = float(bar.iloc[entry_i]["close"])
    if entry <= 0:
        return None
    fut = bar.iloc[entry_i + 1 : entry_i + 1 + max_h]
    high = fut["high"].to_numpy(dtype=float)
    low = fut["low"].to_numpy(dtype=float)
    if side == "BOTTOM":
        mfe = float(high.max() / entry - 1.0)
        mae = float(1.0 - low.min() / entry)
        sign = 1.0
    else:
        mfe = float(1.0 - low.min() / entry)
        mae = float(high.max() / entry - 1.0)
        sign = -1.0
    out = {"entry": entry, "mfe_16": mfe, "mae_16": mae}
    for n in HOLDS:
        close_n = float(bar.iloc[entry_i + n]["close"])
        gross = sign * (close_n / entry - 1.0)
        out[f"ret_{n}"] = gross
        out[f"ret_{n}_net"] = gross - FEE_RT
    return out
