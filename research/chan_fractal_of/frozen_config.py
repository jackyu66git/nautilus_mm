"""CHAN_FRACTAL_OF_001 Phase A lock. Characterization only. No replay runner."""
from __future__ import annotations

FORBIDDEN_PHASE_A_KEYS = frozenset(
    {
        "B1",
        "B2",
        "LTF_B1",
        "LTF_B2",
        "T1",
        "T2",
        "HTF_ZS",
        "HTF_B1",
        "HTF_B2",
        "HTF_BSP",
        "SMC",
        "MSS",
        "BOS",
        "OB",
        "FVG",
        "Entry",
        "strength_score",
        "absorption_flag",
        "exhaustion_flag",
    }
)

A1_FIELDS = (
    "fx_id",
    "fx_side",
    "T_FX_FORMING",
    "T_FX_VISIBLE",
    "of_taker_buy",
    "of_taker_sell",
    "of_delta",
    "of_volume",
    "of_imbalance",
)

A3_FIELDS = (
    "of_delta_forming",
    "of_delta_visible",
    "of_imbalance_forming",
    "of_imbalance_visible",
    "of_sign_flip_forming_to_visible",
)


def assert_phase_a_clean(record: dict) -> None:
    hit = FORBIDDEN_PHASE_A_KEYS.intersection(record)
    if hit:
        raise ValueError(f"Phase A ledger polluted: {sorted(hit)}")


def assert_phase_b_features_clean(record: dict) -> None:
    """Labels may exist; they must not be used as OF inputs."""
    assert_phase_a_clean({k: v for k, v in record.items() if not k.startswith("label_")})


PHASE_B_LABELS = (
    "label_bi_endpoint",
    "label_B1",
    "label_B1_B2",
)

PHASE_B_FEATURES = (
    "of_delta_forming",
    "of_imbalance_forming",
    "of_volume_forming",
    "of_taker_buy_forming",
    "of_taker_sell_forming",
)

PHASE_B_CONFOUND = ("mid_range",)

# Romano et al. small-effect floor for Cliff's δ. Diagnostic, not an OF trading threshold.
CLIFF_NEGLIGIBLE = 0.147
MIN_POS_B1_B2 = 5
N_AMP_BINS = 3
MIN_BIN_POS = 3
MIN_BIN_NEG = 5
