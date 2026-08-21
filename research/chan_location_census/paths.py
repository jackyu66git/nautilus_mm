from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_location_census" / "CHAN_LOCATION_CENSUS_001"
EXPECTED_N_15M = 8641
EXPECTED_N_EVENT = 47
EXPECTED_H1_EXTEND = 27
CELL_MIN = 5
E1 = ROOT / "logs" / "chan_1st_point_fate" / "CHAN_1ST_POINT_FATE_001" / "EVENTS.jsonl"
E2 = ROOT / "logs" / "chan_2nd_point_fate" / "CHAN_2ND_POINT_FATE_001" / "EVENTS.jsonl"
E3 = ROOT / "logs" / "chan_3rd_point_fate" / "CHAN_3RD_POINT_FATE_001" / "EVENTS.jsonl"
E3_MOTHER = ROOT / "logs" / "chan_3rd_point" / "CHAN_3RD_POINT_001" / "EVENTS.jsonl"
CONT = ROOT / "logs" / "chan_cont_null" / "CHAN_CONT_NULL_001" / "EVENTS.jsonl"
