"""Setup_CANDIDATE census. Tape row order only. No outcomes."""
from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from chan_setup_definition.paths import SPAN_DAYS
from chan_setup_definition.schema import CENSUS_EVENT_FIELDS, assert_census_clean

FX_OK = frozenset({"TOP", "BOTTOM"})


def _ts(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value)


def _valid_fx(row: dict) -> bool:
    fx_id = row.get("ltf_fx_id")
    return bool(fx_id) and row.get("ltf_fx") in FX_OK


def scan_candidates(rows: list[dict]) -> list[dict]:
    """Birth = first Tape row of this ltf_fx_id, and leftover already exists.

    Identity is consumed on first sight, even if leftover==0.
    Duration is the first contiguous run after birth. Later reappearance
    does not create a new setup_id and does not reopen duration.
    """
    seen: set[str] = set()
    events: list[dict] = []
    by_id: dict[str, dict] = {}
    live_id: str | None = None

    for i, row in enumerate(rows):
        if not _valid_fx(row):
            live_id = None
            continue
        fx_id = str(row["ltf_fx_id"])
        first = fx_id not in seen
        seen.add(fx_id)
        leftover_ok = int(row.get("htf_anchor_count") or 0) >= 1

        if first:
            if leftover_ok:
                t = str(row["t"])
                rec = {
                    "setup_id": fx_id,
                    "T_SETUP_VISIBLE": t,
                    "T_SETUP_END": t,
                    "duration_bars": 1,
                    "duration_hours": 0.0,
                    "htf_anchor_count": int(row["htf_anchor_count"]),
                    "ltf_fx": row["ltf_fx"],
                    "tape_row": i,
                }
                assert_census_clean(rec)
                events.append(rec)
                by_id[fx_id] = rec
                live_id = fx_id
            else:
                live_id = None
            continue

        if live_id == fx_id and fx_id in by_id:
            rec = by_id[fx_id]
            rec["T_SETUP_END"] = str(row["t"])
            rec["duration_bars"] = int(rec["duration_bars"]) + 1
        else:
            live_id = None

    for rec in events:
        rec["duration_hours"] = round(
            float((_ts(rec["T_SETUP_END"]) - _ts(rec["T_SETUP_VISIBLE"])).total_seconds() / 3600.0),
            6,
        )
        assert_census_clean(rec)
        extra = set(rec) - set(CENSUS_EVENT_FIELDS)
        if extra:
            raise ValueError(f"census extra keys: {sorted(extra)}")
    return events


def _quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"n": 0, "min": None, "p50": None, "max": None}
    s = pd.Series(values, dtype="float64")
    return {
        "n": int(len(values)),
        "min": float(s.min()),
        "p50": float(s.median()),
        "max": float(s.max()),
    }


def summarize(rows: list[dict], events: list[dict]) -> dict:
    n_rows = len(rows)
    n_leftover = sum(1 for r in rows if int(r.get("htf_anchor_count") or 0) >= 1)
    n_fx = sum(1 for r in rows if _valid_fx(r))
    first_seen_leftover0 = 0
    seen: set[str] = set()
    for r in rows:
        if not _valid_fx(r):
            continue
        fx_id = str(r["ltf_fx_id"])
        if fx_id in seen:
            continue
        seen.add(fx_id)
        if int(r.get("htf_anchor_count") or 0) < 1:
            first_seen_leftover0 += 1

    n = len(events)
    durations = [float(e["duration_hours"]) for e in events]
    duration_bars = [int(e["duration_bars"]) for e in events]
    gaps_h: list[float] = []
    for a, b in zip(events, events[1:]):
        dt = _ts(b["T_SETUP_VISIBLE"]) - _ts(a["T_SETUP_VISIBLE"])
        gaps_h.append(float(dt.total_seconds()) / 3600.0)
    anchors = Counter(int(e["htf_anchor_count"]) for e in events)
    sides = Counter(str(e["ltf_fx"]) for e in events)

    first_t = str(rows[0]["t"]) if rows else None
    last_t = str(rows[-1]["t"]) if rows else None
    return {
        "n_tape_rows": n_rows,
        "span_days": SPAN_DAYS,
        "first_t": first_t,
        "last_t": last_t,
        "n_rows_leftover_ge1": n_leftover,
        "n_rows_valid_fx": n_fx,
        "n_unique_fx_id": len(seen),
        "n_fx_id_consumed_leftover0": first_seen_leftover0,
        "n_setup": n,
        "per_day": round(n / SPAN_DAYS, 6) if SPAN_DAYS else None,
        "per_1000_bars": round(n / n_rows * 1000.0, 6) if n_rows else None,
        "duration_hours": _quantiles(durations),
        "duration_bars": _quantiles(duration_bars),
        "interval_hours": _quantiles(gaps_h),
        "htf_anchor_count_at_birth": dict(sorted(anchors.items())),
        "ltf_fx_at_birth": dict(sides),
    }
