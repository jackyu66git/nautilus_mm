from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
FROZEN_15M = ROOT / "logs" / "chan_3rd_point" / "CHAN_3RD_POINT_001" / "EVENTS.jsonl"
LOG = ROOT / "logs" / "chan_3buy_15m_universe" / "CHAN_3BUY_15M_UNIVERSE_001"
EXPECTED_N_15M = 8641
FROZEN_N_3 = 20
