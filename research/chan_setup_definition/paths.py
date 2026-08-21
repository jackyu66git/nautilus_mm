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
LOG = ROOT / "logs" / "chan_setup_definition" / "CHAN_SETUP_DEFINITION_001"
BAR_MINUTES = 15
SPAN_DAYS = 90.00
EXPECTED_N_15M = 8641
