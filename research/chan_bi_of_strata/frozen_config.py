"""CHAN_BI_OF_STRATA_001. Confirmed bi-endpoint OF quintiles. No B1/B2."""
from __future__ import annotations

FORBIDDEN = frozenset({"B1", "B2", "label_B1", "label_B1_B2", "HTF_ZS", "SMC", "Entry", "strength_score"})

HOLDS = (4, 8, 16)
FEE_RT = 0.0008  # 2 × taker 4bps
N_QUINT = 5
MIN_PER_Q = 15
RHO_MONOTONE = 0.6  # Spearman of 5 bucket medians; not an OF threshold
BAR_MINUTES = 15


def assert_clean(record: dict) -> None:
    hit = FORBIDDEN.intersection(record)
    if hit:
        raise ValueError(f"CHAN_BI_OF_STRATA_001 ledger polluted: {sorted(hit)}")
