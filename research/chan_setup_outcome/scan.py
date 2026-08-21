"""First structural event after Setup_CANDIDATE birth. Tape only."""
from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from chan_setup_outcome.paths import DIRS, EXPECTED_N_SETUP, FX_OK, SPAN_DAYS
from chan_setup_outcome.schema import LABEL_B2, assert_outcome_clean, classify


def _ts(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value)


def _valid_fx(row: dict) -> bool:
    return bool(row.get("ltf_fx_id")) and row.get("ltf_fx") in FX_OK


def detect_event(row: dict, s0_fx_id: str, s0_bi_dir: Any, s0_bi_sure: bool) -> str | None:
    rdir = row.get("ltf_bi_dir")
    if s0_bi_dir in DIRS and rdir in DIRS and s0_bi_dir != rdir:
        return "BI_DIR_CHANGE"
    rsure = row.get("ltf_bi_sure")
    if s0_bi_sure is True and rsure is False:
        return "BI_SURE_OFF"
    if s0_bi_sure is False and rsure is True:
        return "BI_SURE_ON"
    if not _valid_fx(row) or str(row.get("ltf_fx_id")) != s0_fx_id:
        return "FX_IDENTITY_CHANGE"
    return None


def scan_one(rows: list[dict], setup: dict) -> dict | None:
    i0 = int(setup["tape_row"])
    birth = rows[i0]
    if str(birth["t"]) != str(setup["T_SETUP_VISIBLE"]):
        raise ValueError(f"tape_row clock mismatch setup_id={setup['setup_id']}")
    if i0 >= len(rows) - 1:
        return None
    s0_fx_id = str(setup["setup_id"])
    s0_bi_dir = birth.get("ltf_bi_dir")
    s0_bi_sure = bool(birth.get("ltf_bi_sure"))
    # bool(None)==False would mis-fire SURE_ON. Only True/False count as sure state.
    if birth.get("ltf_bi_sure") is None:
        s0_bi_sure = False
    label_b1 = False
    event = None
    j_hit = None
    for j in range(i0 + 1, len(rows)):
        row = rows[j]
        if row.get("b1_lock") is True:
            label_b1 = True
        event = detect_event(row, s0_fx_id, s0_bi_dir, s0_bi_sure)
        if event is not None:
            j_hit = j
            break
    if event is None:
        event = "CENSOR"
        j_hit = len(rows) - 1
    rec = {
        "setup_id": s0_fx_id,
        "T_SETUP_VISIBLE": str(setup["T_SETUP_VISIBLE"]),
        "T_OUTCOME_VISIBLE": str(rows[j_hit]["t"]),
        "outcome_event": event,
        "outcome_class": classify(event, s0_bi_sure),
        "label_b1": bool(label_b1),
        "label_b2": LABEL_B2,
        "duration_hours": round(
            float((_ts(rows[j_hit]["t"]) - _ts(setup["T_SETUP_VISIBLE"])).total_seconds() / 3600.0),
            6,
        ),
        "tape_row": i0,
        "outcome_row": int(j_hit),
    }
    assert_outcome_clean(rec)
    if rec["T_SETUP_VISIBLE"] == rec["T_OUTCOME_VISIBLE"]:
        raise ValueError(f"T_SETUP_VISIBLE not < T_OUTCOME_VISIBLE setup_id={s0_fx_id}")
    return rec


def scan_outcomes(rows: list[dict], setups: list[dict]) -> tuple[list[dict], list[str]]:
    if len(setups) != EXPECTED_N_SETUP:
        raise ValueError(f"mother set drift n={len(setups)} expected={EXPECTED_N_SETUP}")
    records = []
    clock_drop = []
    for s in setups:
        rec = scan_one(rows, s)
        if rec is None:
            clock_drop.append(str(s["setup_id"]))
        else:
            records.append(rec)
    return records, clock_drop


def _quantiles(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "min": None, "p50": None, "max": None}
    s = pd.Series(values, dtype="float64")
    return {"n": int(len(values)), "min": float(s.min()), "p50": float(s.median()), "max": float(s.max())}


def summarize(records: list[dict], clock_drop: list[str] | None = None) -> dict:
    n = len(records)
    drop = list(clock_drop or [])
    by_event = Counter(r["outcome_event"] for r in records)
    by_class = Counter(r["outcome_class"] for r in records)
    b1_true = [r for r in records if r["label_b1"] is True]
    b1_by_class = Counter(r["outcome_class"] for r in b1_true)
    b1_by_event = Counter(r["outcome_event"] for r in b1_true)
    durations = [float(r["duration_hours"]) for r in records]
    return {
        "n_mother": EXPECTED_N_SETUP,
        "n_setup": n,
        "n_clock_drop": len(drop),
        "clock_drop_ids": drop,
        "span_days": SPAN_DAYS,
        "outcome_class": {k: int(by_class.get(k, 0)) for k in ("CONTINUES", "REVERSES", "DISSOLVES", "NEXT_EVENT", "CENSOR")},
        "outcome_event": {k: int(by_event.get(k, 0)) for k in ("BI_SURE_ON", "BI_DIR_CHANGE", "BI_SURE_OFF", "FX_IDENTITY_CHANGE", "CENSOR")},
        "n_censor": int(by_class.get("CENSOR", 0)),
        "label_b1_true": len(b1_true),
        "label_b1_false": n - len(b1_true),
        "label_b1_by_outcome_class": dict(b1_by_class),
        "label_b1_by_outcome_event": dict(b1_by_event),
        "label_b2": LABEL_B2,
        "duration_hours": _quantiles(durations),
    }
