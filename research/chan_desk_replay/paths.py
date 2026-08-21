from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
DATA = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP"
LOG = ROOT / "logs" / "chan_desk_replay" / "CHAN_DESK_REPLAY_001" / "TAPE-90D-1H-15M"
KLINE_1M = DATA / "1m.parquet"
OF_1M = DATA / "1m_of.parquet"
AGG_DAILY = DATA / "aggTrades" / "daily"
TAPE_START = "2026-05-21T10:39:00+00:00"
TAPE_END = "2026-08-19T10:38:00+00:00"
