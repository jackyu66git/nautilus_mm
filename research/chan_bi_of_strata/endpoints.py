"""Sure-bi endpoints with T_BI_SURE. Earliest confirmation. No B1/B2."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from chanlun.core.ChanEnum import Chan_BI_DIR
from chanlun.pipeline.timeframe import TF_DF
from chan_bi_of_strata.frozen_config import BAR_MINUTES


def _ts(text) -> pd.Timestamp:
    t = pd.Timestamp(text)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    return t


@dataclass
class ConfirmedEndpoint:
    fx_id: str
    side: str
    T_BI_SURE: pd.Timestamp
    bi_index: int


def extract_confirmed_endpoints(engine: TF_DF, bar_minutes: int = BAR_MINUTES) -> list[ConfirmedEndpoint]:
    """End of a sure pen. T_BI_SURE = confirming KLC last bar close."""
    by_fx: dict[str, ConfirmedEndpoint] = {}
    for bi in engine.bi_list:
        if not bi.is_sure or bi.end_klc is None or bi.sure_time is None:
            continue
        side = "BOTTOM" if bi.dir == Chan_BI_DIR.DOWN else "TOP"
        fx_id = bi.end_klc.start_time
        t_sure = _ts(bi.sure_time) + pd.Timedelta(minutes=bar_minutes)
        prev = by_fx.get(fx_id)
        if prev is None or t_sure < prev.T_BI_SURE:
            by_fx[fx_id] = ConfirmedEndpoint(fx_id, side, t_sure, bi.index)
    return list(by_fx.values())
