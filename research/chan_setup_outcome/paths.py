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
CENSUS_EVENTS = (
    ROOT
    / "logs"
    / "chan_setup_definition"
    / "CHAN_SETUP_DEFINITION_001"
    / "CENSUS_EVENTS.jsonl"
)
LOG = ROOT / "logs" / "chan_setup_outcome" / "CHAN_SETUP_OUTCOME_001"
EXPECTED_N_SETUP = 2342
EXPECTED_N_15M = 8641
SPAN_DAYS = 90.00
DIRS = frozenset({"UP", "DOWN"})
FX_OK = frozenset({"TOP", "BOTTOM"})
