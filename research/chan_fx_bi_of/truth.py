"""Sure-bi endpoints only. Never find_all_bsp / B1 / B2."""
from __future__ import annotations

from dataclasses import dataclass, field

from chanlun.pipeline.timeframe import TF_DF


@dataclass
class BiOnlyIndex:
    endpoints: set[str] = field(default_factory=set)
    n_sure_bi: int = 0
    n_unsure_bi: int = 0


def extract_bi_only(engine: TF_DF) -> BiOnlyIndex:
    out = BiOnlyIndex()
    for bi in engine.bi_list:
        if not bi.is_sure:
            out.n_unsure_bi += 1
            continue
        out.n_sure_bi += 1
        if bi.start_klc is not None:
            out.endpoints.add(bi.start_klc.start_time)
        if bi.end_klc is not None:
            out.endpoints.add(bi.end_klc.start_time)
    return out
