# CHAN_TRADE_OF_001 Phase 0 lock. No absorption detector.
from __future__ import annotations

FORBIDDEN_KEYS = frozenset(
    {
        "B1",
        "B2",
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
        "absorption_flag",
        "exhaustion_flag",
        "sweep_flag",
    }
)

# F1: reconstructed delta vs kline delta. Not a trading threshold.
F1_SPEARMAN_MIN = 0.95
F1_MED_REL_MAX = 0.15

# F2: feature ≈ delta+volume+range if |Spearman| with that plane is high.
# Multiple R via Spearman with |delta|, volume, mid_range: take max abs.
# Independent if at least one of {hhi, speed, push} has max|ρ| < this AND
# within similar volume/range the spread remains material.
F2_REWRITE_RHO = 0.70
F2_WITHIN_CV_MIN = 0.25

TICK = 0.1  # BTCUSDT-PERP

# Phase 1: HHI → push after controlling |delta| and volume. Not an edge threshold.
P1_N_BINS = 3
P1_MIN_CELL = 40
P1_RHO_STABLE = 0.30
P1_MIN_AGREE = 6

# Phase 2: mechanism vs artifact. Not an edge threshold. Sign frozen from Phase 1 (HHI↑ → push↓).
P2_N_BINS = 3
P2_SLICE_RHO = 0.20
P2_ARTIFACT_FLOOR = 0.20
P2_EXTREME_P = 95
P2_SIGN = -1.0
P2_MIN_N = 80


def assert_clean(record: dict) -> None:
    hit = FORBIDDEN_KEYS.intersection(record)
    if hit:
        raise ValueError(f"CHAN_TRADE_OF_001 ledger polluted: {sorted(hit)}")
