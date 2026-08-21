from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_cont_null" / "CHAN_CONT_NULL_001"
EXPECTED_N_15M = 8641
E1 = ROOT / "logs" / "chan_1st_point_fate" / "CHAN_1ST_POINT_FATE_001" / "EVENTS.jsonl"
E2 = ROOT / "logs" / "chan_2nd_point_fate" / "CHAN_2ND_POINT_FATE_001" / "EVENTS.jsonl"
E3 = ROOT / "logs" / "chan_3rd_point_fate" / "CHAN_3RD_POINT_FATE_001" / "EVENTS.jsonl"
DELTA_NO_INCREMENT = 0.05
