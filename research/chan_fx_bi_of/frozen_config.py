"""CHAN_FX_BI_OF_001. Ordinary fractal vs bi-endpoint. No B1/B2."""
from __future__ import annotations

FORBIDDEN_KEYS = frozenset(
    {
        "B1",
        "B2",
        "label_B1",
        "label_B1_B2",
        "HTF_ZS",
        "SMC",
        "Entry",
        "strength_score",
    }
)

FEATURES = (
    "of_delta_forming",
    "of_imbalance_forming",
    "of_volume_forming",
    "of_taker_buy_forming",
    "of_taker_sell_forming",
)

LABEL = "label_bi_endpoint"
CONFOUND = ("mid_range",)

CLIFF_NEGLIGIBLE = 0.147
MIN_GROUP = 50
N_AMP_BINS = 3
MIN_BIN_POS = 15
MIN_BIN_NEG = 30


def assert_clean(record: dict) -> None:
    hit = FORBIDDEN_KEYS.intersection(record)
    if hit:
        raise ValueError(f"CHAN_FX_BI_OF_001 ledger polluted: {sorted(hit)}")
