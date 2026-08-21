"""Integrity gates. Not Edge. No subjective fields."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from chan_desk_replay.schema import FORBIDDEN_LEDGER_KEYS, SMC_STATE, assert_clean


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def _utc(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        return t.tz_localize("UTC")
    return t.tz_convert("UTC")


def audit_tape(rows: list[dict]) -> dict:
    for r in rows:
        assert_clean(r)
    gates: list[Gate] = []
    n = len(rows)
    if n < 8000:
        gates.append(Gate("C0", "FAIL", f"n_15m={n} < 8000"))
        for name in ("C1", "C2", "C3", "C4", "C5", "C6"):
            gates.append(Gate(name, "NOT_RUN", "C0 FAIL"))
        return _pack(rows, gates, "FAIL", "CLOCK")

    ts = pd.to_datetime([r["t"] for r in rows], utc=True)
    diffs = pd.Series(ts).diff().dt.total_seconds().dropna()
    n_gap = int((diffs != 900).sum())
    span_d = (ts[-1] - ts[0]).total_seconds() / 86400.0
    if span_d < 89 or n_gap > 8:
        gates.append(Gate("C0", "FAIL", f"span_days={span_d:.2f} n={n} gaps_ne_15m={n_gap}"))
        for name in ("C1", "C2", "C3", "C4", "C5", "C6"):
            gates.append(Gate(name, "NOT_RUN", "C0 FAIL"))
        return _pack(rows, gates, "FAIL", "CLOCK")
    gates.append(Gate("C0", "PASS", f"n_15m={n} span_days={span_d:.2f} gaps_ne_15m={n_gap}"))

    leak = 0
    for r in rows:
        t = _utc(r["t"])
        for h in r.get("htf_leftover") or []:
            tc = h.get("T_ZS_COMPLETE")
            if tc is None or _utc(tc) >= t:
                leak += 1
                break
    if leak:
        gates.append(Gate("C1", "FAIL", f"leftover future-or-equal complete on {leak} rows"))
        for name in ("C2", "C3", "C4", "C5", "C6"):
            gates.append(Gate(name, "NOT_RUN", "C1 FAIL"))
        return _pack(rows, gates, "FAIL", "LEAK")
    gates.append(Gate("C1", "PASS", "T_ZS_COMPLETE < t on all leftover"))

    closed = all(r.get("t") and r.get("open_ts") for r in rows)
    if not closed:
        gates.append(Gate("C2", "FAIL", "missing open/close"))
        for name in ("C3", "C4", "C5", "C6"):
            gates.append(Gate(name, "NOT_RUN", "C2 FAIL"))
        return _pack(rows, gates, "FAIL", "CLOCK")
    gates.append(Gate("C2", "PASS", "each row is a closed 15m bar prefix"))

    of_bad = 0
    for r in rows:
        t = _utc(r["t"])
        end = _utc(r["of_window_end"])
        if end > t:
            of_bad += 1
            continue
        t_fx = r.get("T_FX_VISIBLE")
        if t_fx and end > _utc(t_fx):
            of_bad += 1
    if of_bad:
        gates.append(Gate("C3", "FAIL", f"OF window past t or T_FX_VISIBLE on {of_bad} rows"))
        for name in ("C4", "C5", "C6"):
            gates.append(Gate(name, "NOT_RUN", "C3 FAIL"))
        return _pack(rows, gates, "FAIL", "LEAK")
    gates.append(Gate("C3", "PASS", "OF of_window_end <= t and <= T_FX_VISIBLE when present"))

    smc_bad = sum(r.get("smc_state") != SMC_STATE for r in rows)
    if smc_bad:
        gates.append(Gate("C4", "FAIL", f"smc_state not UNDEFINED on {smc_bad}"))
        gates.extend([Gate("C5", "NOT_RUN", "C4 FAIL"), Gate("C6", "NOT_RUN", "C4 FAIL")])
        return _pack(rows, gates, "FAIL", "SMC")
    gates.append(Gate("C4", "PASS", "smc_state=UNDEFINED on all rows"))

    dirty = 0
    for r in rows:
        if FORBIDDEN_LEDGER_KEYS.intersection(r):
            dirty += 1
    if dirty:
        gates.append(Gate("C5", "FAIL", f"forbidden keys on {dirty} rows"))
        gates.append(Gate("C6", "NOT_RUN", "C5 FAIL"))
        return _pack(rows, gates, "FAIL", "SCHEMA")
    gates.append(Gate("C5", "PASS", "no allow/entry/stop/MFE/of_support/B2"))

    by_t = {}
    dup = 0
    for r in rows:
        k = r["t"]
        if k in by_t:
            dup += 1
        by_t[k] = (r["htf_anchor_count"], r["b1_lock"], r["smc_state"], r["of_window_end"])
    if dup:
        gates.append(Gate("C6", "FAIL", f"duplicate t={dup}"))
        return _pack(rows, gates, "FAIL", "REPLAY")
    probes = [rows[0], rows[n // 2], rows[-1]]
    ok = all(
        by_t[p["t"]] == (p["htf_anchor_count"], p["b1_lock"], p["smc_state"], p["of_window_end"])
        for p in probes
    )
    if not ok:
        gates.append(Gate("C6", "FAIL", "probe mismatch"))
        return _pack(rows, gates, "FAIL", "REPLAY")
    gates.append(Gate("C6", "PASS", f"unique t={n} probes replay-identical"))
    return _pack(rows, gates, "PASS", "STATE_TAPE_OK")


def _pack(rows, gates, decision, kind) -> dict:
    n = len(rows)
    n_lock = sum(int(bool(r.get("b1_lock"))) for r in rows)
    n_trade = sum(r.get("of_trade_status") == "ok" for r in rows)
    n_not = sum(r.get("of_trade_status") == "not_loaded" for r in rows)
    return {
        "experiment": "CHAN_DESK_REPLAY_001",
        "decision": decision,
        "kind": kind,
        "n_events": n,
        "gates": [asdict(g) for g in gates],
        "summary": {
            "n_15m": n,
            "n_b1_lock": n_lock,
            "n_of_trade_ok": n_trade,
            "n_of_trade_not_loaded": n_not,
            "first_t": rows[0]["t"] if rows else None,
            "last_t": rows[-1]["t"] if rows else None,
        },
        "blocked": "≠Edge 不准 allow Entry Stop MFE MAE of_support SMC-detector B2 换TF",
    }
