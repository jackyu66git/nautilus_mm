from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_b3_exit_census" / "CHAN_B3_EXIT_CENSUS_001"
E3_MOTHER = ROOT / "logs" / "chan_3rd_point" / "CHAN_3RD_POINT_001" / "EVENTS.jsonl"
EXPECTED_N_15M = 8641
EXPECTED_N_EVENT = 20
EXPECTED_N_B3 = 12
EXPECTED_N_S3 = 8
R_GRID = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
HORIZON_H = (24, 48, 72)
BAR_H = 0.25
BARS_PER_H = 4
DELTA_PP = 0.20
A_MIN_HIT = 0.40
