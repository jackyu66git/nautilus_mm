"""CHAN_SETUP_OUTCOME_001 vocabulary lock. No scan."""
from __future__ import annotations

OUTCOME_EVENTS = (
    "BI_DIR_CHANGE",
    "BI_SURE_OFF",
    "BI_SURE_ON",
    "FX_IDENTITY_CHANGE",
    "CENSOR",
)

OUTCOME_CLASSES = (
    "CONTINUES",
    "REVERSES",
    "DISSOLVES",
    "NEXT_EVENT",
    "CENSOR",
)

# Same-bar precedence. b1_lock is not in this race.
EVENT_PRECEDENCE = (
    "BI_DIR_CHANGE",
    "BI_SURE_OFF",
    "BI_SURE_ON",
    "FX_IDENTITY_CHANGE",
)

LABEL_B2 = "UNAVAILABLE"

OUTCOME_RECORD_FIELDS = (
    "setup_id",
    "T_SETUP_VISIBLE",
    "T_OUTCOME_VISIBLE",
    "outcome_event",
    "outcome_class",
    "label_b1",
    "label_b2",
    "duration_hours",
    "tape_row",
    "outcome_row",
)


def classify(event: str, s0_bi_sure: bool) -> str:
    if event == "BI_SURE_ON":
        return "CONTINUES"
    if event == "BI_DIR_CHANGE":
        return "REVERSES"
    if event == "BI_SURE_OFF":
        return "DISSOLVES"
    if event == "FX_IDENTITY_CHANGE":
        return "NEXT_EVENT" if s0_bi_sure else "DISSOLVES"
    if event == "CENSOR":
        return "CENSOR"
    raise ValueError(f"unknown outcome_event: {event}")


def assert_outcome_clean(record: dict) -> None:
    hit = FORBIDDEN_OUTCOME_KEYS.intersection(record)
    if hit:
        raise ValueError(f"outcome polluted: {sorted(hit)}")
    extra = set(record) - set(OUTCOME_RECORD_FIELDS)
    if extra:
        raise ValueError(f"outcome extra keys: {sorted(extra)}")
    if record.get("label_b2") != LABEL_B2:
        raise ValueError("label_b2 must be UNAVAILABLE")
    if record.get("outcome_event") == "B1_LOCK":
        raise ValueError("b1_lock is not an outcome_event")


FORBIDDEN_OUTCOME_KEYS = frozenset(
    {
        "MFE",
        "MAE",
        "WR",
        "PF",
        "expectancy",
        "Entry",
        "Stop",
        "allow",
        "success",
        "fail",
        "win",
        "of_kline_delta",
        "of_hhi",
        "of_push",
        "of_speed",
        "of_support",
        "smc_state",
        "CONTACT",
        "T_FX_VISIBLE",
        "htf_living",
        "B2",
        "LTF_B2",
        "label_b2_true",
        "excursion",
        "up_excursion",
        "down_excursion",
    }
)
