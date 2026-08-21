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
OUTCOME_EVENTS = (
    ROOT
    / "logs"
    / "chan_setup_outcome"
    / "CHAN_SETUP_OUTCOME_001"
    / "OUTCOME_EVENTS.jsonl"
)
LOG = ROOT / "logs" / "chan_setup_strata" / "CHAN_SETUP_STRATA_001"
EXPECTED_N_MOTHER = 2342
EXPECTED_N_OUTCOME = 2341
EXPECTED_N_15M = 8641
