from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
TAPE = (
    ROOT
    / "logs"
    / "chan_desk_replay"
    / "CHAN_DESK_REPLAY_001"
    / "TAPE-90D-1H-15M"
    / "TAPE.jsonl"
)
KLINE_1M = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "1m.parquet"
LOG = ROOT / "logs" / "chan_htf_zs_ltf_rev" / "CHAN_HTF_ZS_LTF_REV_001"
EXPECTED_N_15M = 8641
