"""CHAN_FX_BI_TRADE_OF_001. Complete OF × bi-endpoint. No B1/B2. No HHI mechanism."""
from __future__ import annotations

FORBIDDEN_KEYS = frozenset(
    {
        "B1",
        "B2",
        "label_B1",
        "label_B1_B2",
        "T1",
        "T2",
        "HTF_ZS",
        "SMC",
        "MSS",
        "BOS",
        "OB",
        "FVG",
        "Entry",
        "strength_score",
        "combo_score",
        "absorption_flag",
        "exhaustion_flag",
        "sweep_flag",
    }
)

FEATURES_NEW = ("hhi", "push")
FEATURE_DELTA = "kline_delta"
LABEL = "label_bi_endpoint"

# Same floors as CHAN_FX_BI_OF_001. Not a trading threshold.
CLIFF_NEGLIGIBLE = 0.147
MIN_GROUP = 50
N_BINS = 3
MIN_BIN_POS = 15
MIN_BIN_NEG = 30

# Baseline replication: bottoms, more-negative delta → more bi-like.
DELTA_SIGN = -1.0
BASELINE_N_BOTTOM = 978
BASELINE_N_ORDINARY = 842
BASELINE_N_BI = 136


def assert_clean(record: dict) -> None:
    hit = FORBIDDEN_KEYS.intersection(record)
    if hit:
        raise ValueError(f"CHAN_FX_BI_TRADE_OF_001 ledger polluted: {sorted(hit)}")
