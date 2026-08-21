from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
DATA = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP"
LOG = ROOT / "logs" / "chan_bi_of_strata_5m" / "CHAN_BI_OF_STRATA_005M_001" / "SMOKE-60D-5M"
KLINE_1M = DATA / "1m.parquet"
OF_1M = DATA / "1m_of.parquet"
BAR_MINUTES = 5
