"""Four pre-registered one-way tables. Birth X, frozen Outcome Y."""
from __future__ import annotations

from collections import Counter, defaultdict

from chan_setup_strata.schema import (
    BI_STATES,
    FX_SIDES,
    OUTCOME_CLASSES,
    SPACE_RELS,
    bi_state,
    space_rel,
)


def assign_x(birth: dict) -> dict:
    fx = birth.get("ltf_fx")
    if fx not in FX_SIDES:
        raise ValueError(f"birth fx not TOP/BOTTOM: {fx}")
    leftover = birth.get("htf_leftover") or []
    if int(birth.get("htf_anchor_count") or 0) < 1 or not leftover:
        raise ValueError("birth has no leftover")
    return {
        "anchor_n": int(birth["htf_anchor_count"]),
        "space_rel": space_rel(leftover),
        "bi_state": bi_state(birth.get("ltf_bi_dir"), birth.get("ltf_bi_sure")),
        "fx_side": fx,
    }


def join_rows(tape: list[dict], outcomes: list[dict]) -> list[dict]:
    rows = []
    for o in outcomes:
        i = int(o["tape_row"])
        birth = tape[i]
        if str(birth["t"]) != str(o["T_SETUP_VISIBLE"]):
            raise ValueError(f"clock mismatch setup_id={o['setup_id']}")
        rec = assign_x(birth)
        rec["setup_id"] = o["setup_id"]
        rec["outcome_class"] = o["outcome_class"]
        if rec["outcome_class"] not in OUTCOME_CLASSES:
            raise ValueError(f"unknown outcome_class {rec['outcome_class']}")
        rows.append(rec)
    return rows


def _table(rows: list[dict], key: str, levels: tuple | None) -> list[dict]:
    buckets: dict = defaultdict(Counter)
    for r in rows:
        buckets[r[key]][r["outcome_class"]] += 1
    if levels is None:
        order = sorted(buckets, key=lambda x: (isinstance(x, str), x))
    else:
        order = list(levels)
    out = []
    for level in order:
        c = buckets.get(level) or Counter()
        n = int(sum(c.values()))
        rec = {"level": level, "n": n}
        for cls in OUTCOME_CLASSES:
            rec[cls] = int(c.get(cls, 0))
        rec["dissolves_share"] = round(rec["DISSOLVES"] / n, 6) if n else None
        out.append(rec)
    return out


def build_tables(rows: list[dict]) -> dict:
    return {
        "htf_leftover_count": _table(rows, "anchor_n", None),
        "space_relation": _table(rows, "space_rel", SPACE_RELS),
        "bi_state": _table(rows, "bi_state", BI_STATES),
        "fractal_direction": _table(rows, "fx_side", FX_SIDES),
    }


def clock_drop_ids(census: list[dict], outcomes: list[dict]) -> list[str]:
    got = {o["setup_id"] for o in outcomes}
    return [str(s["setup_id"]) for s in census if s["setup_id"] not in got]
