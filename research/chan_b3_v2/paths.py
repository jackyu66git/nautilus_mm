from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_b3_v2" / "CHAN_B3_V2"
E3_MOTHER = ROOT / "logs" / "chan_3rd_point" / "CHAN_3RD_POINT_001" / "EVENTS.jsonl"
EXPECTED_N_15M = 8641
EXPECTED_N_EVENT = 20
EXPECTED_N_B3 = 12
EXPECTED_N_S3 = 8
ACCOUNT = 100_000.0
RISK_FRAC = 0.005
TIME_BARS = 96
BAR_H = 0.25
TP_VARIANTS = (("V2_050", 0.5), ("V2_075", 0.75), ("V2_100", 1.0))
V1_TIME_SHARE = 0.60
V1_AVG_R = -0.029004
V1_WIN = 4
V1_LOSS = 4
V1_TIME = 12
TIME_DROP = 0.20
AVG_IMPROVE = 0.10
FAMILY_CONFLICT = 0.10
