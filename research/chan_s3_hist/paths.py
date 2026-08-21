from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
DATA = ROOT / "data" / "chan_s3_hist" / "BTCUSDT-PERP"
KLINE_1M = DATA / "1m.parquet"
LOG = ROOT / "logs" / "chan_s3_hist" / "CHAN_S3_HIST_001"
ZIP_K = DATA / "klines_zip"
# Burn-in before the census clock. Events before CENSUS_START are dropped.
DATA_START = "2025-02-21T00:00:00+00:00"
CENSUS_START = "2025-05-21T10:39:00+00:00"
# Exclusive. Definition/tuning window starts here. Not OOS. Not Recheck.
CENSUS_END = "2026-05-21T10:39:00+00:00"
ACCOUNT = 100_000.0
TP_MULT = 0.5
PERM_N = 10_000
PERM_SEED = 1
MIN_N = 30
YEAR_MIN_N = 8
HIT24_RANDOM = 0.40
PERM_ALPHA = 0.05
PERM_NULL = 0.10
