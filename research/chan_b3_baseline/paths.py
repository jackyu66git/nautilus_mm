from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_b3_baseline" / "CHAN_B3_BASELINE_V1"
E3_MOTHER = ROOT / "logs" / "chan_3rd_point" / "CHAN_3RD_POINT_001" / "EVENTS.jsonl"
EXPECTED_N_15M = 8641
EXPECTED_N_EVENT = 20
EXPECTED_N_B3 = 12
EXPECTED_N_S3 = 8
ACCOUNT = 100_000.0
RISK_FRAC = 0.005
TIME_BARS = 96  # 24h / 15m
BAR_H = 0.25
