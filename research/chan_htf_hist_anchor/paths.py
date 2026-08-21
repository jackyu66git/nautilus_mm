from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
DATA = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP"
LOG = ROOT / "logs" / "chan_htf_hist_anchor" / "CHAN_HTF_HIST_ANCHOR_LTF_B1_001" / "SMOKE-60D-1H-15M"
KLINE_1M = DATA / "1m.parquet"
LTF_B1_EVENTS = (
    ROOT / "logs" / "chan_htf_zs_ltf_b1" / "CHAN_HTF_ZS_LTF_B1_001" / "SMOKE-60D-1H-15M" / "PHASE_0_EVENTS.jsonl"
)
PHASE0_EVENTS = LOG / "PHASE_0_EVENTS.jsonl"
EARLY_CASES = (
    ROOT / "logs" / "chan_b1_b2_early" / "CHAN_B1_B2_EARLY_001" / "SMOKE-60D-15M" / "cases.jsonl"
)
