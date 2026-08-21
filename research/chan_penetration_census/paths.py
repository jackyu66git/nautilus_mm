from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_penetration_census" / "CHAN_PENETRATION_CENSUS_001"
EXPECTED_N_15M = 8641
EXPECTED_N_EVENT = 47
EXPECTED_N_B1 = 18
EXPECTED_N_B2 = 9
EXPECTED_N_B3 = 20
BUCKET_MIN = 3
BLOB_MAX = 0.90
CONT = ROOT / "logs" / "chan_cont_null" / "CHAN_CONT_NULL_001" / "EVENTS.jsonl"
