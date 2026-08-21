from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
MOTHER = ROOT / "logs" / "chan_3rd_point" / "CHAN_3RD_POINT_001" / "EVENTS.jsonl"
LOG = ROOT / "logs" / "chan_3rd_point_fate" / "CHAN_3RD_POINT_FATE_001"
EXPECTED_N_15M = 8641
EXPECTED_N_3 = 20
N_LEAVE = 57
N_PULLBACK_IN = 37
