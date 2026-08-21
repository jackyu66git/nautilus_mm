from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_ema52_where" / "CHAN_EMA52_WHERE_001"
EXPECTED_N_15M = 8641

EMA_SPAN = 52
ATR_SPAN = 14
AWAY_K = 1.0
NEAR_K = 0.5
TREND_BARS = 8
CHECKPOINT = 4
WARM = 60
