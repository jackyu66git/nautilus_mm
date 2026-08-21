from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
LOG = ROOT / "logs" / "chan_b3_r_census" / "CHAN_B3_R_CENSUS_001"
V1_TRADES = ROOT / "logs" / "chan_b3_baseline" / "CHAN_B3_BASELINE_V1" / "TRADES.jsonl"
EXPECTED_N_EVENT = 20
EXPECTED_N_B3 = 12
EXPECTED_N_S3 = 8
RATIO_P90 = 2.5
RATIO_P95 = 3.0
RATIO_MAX = 5.0
