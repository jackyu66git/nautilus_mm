"""Phase 0 Q1–Q3. No Q4 B1→B2. No OF/SMC."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from chan_htf_hist_anchor.phase0_schema import assert_no_htf_bsp


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def audit_phase0(rows: list[dict]) -> dict:
    for r in rows:
        assert_no_htf_bsp(r)
    b1_ids = []
    seen = set()
    for r in rows:
        k = r["LTF_B1"]
        if k not in seen:
            seen.add(k)
            b1_ids.append(k)
    n_b1 = len(b1_ids)
    gates: list[Gate] = []
    if n_b1 < 1:
        gates.append(Gate("C0", "FAIL", "n_LTF_B1=0"))
        for name in ("C1", "C2", "C3"):
            gates.append(Gate(name, "NOT_RUN", "C0 FAIL"))
        return _pack(rows, gates, "FAIL", "CLOCK", n_b1)

    gates.append(Gate("C0", "PASS", f"n_LTF_B1={n_b1} n_rows={len(rows)}"))

    future = 0
    for r in rows:
        if r.get("NO_HIST_ANCHOR"):
            continue
        t1 = r["T_LTF_B1"]
        for key in ("T_ZG", "T_ZD", "T_GG", "T_DD", "T_ZS_COMPLETE"):
            ts = r.get(key)
            if ts is not None and ts >= t1:
                future += 1
                break
    if future:
        gates.append(Gate("C1", "FAIL", f"T_ANCHOR >= T_LTF_B1 on {future} rows"))
        gates.extend([Gate("C2", "NOT_RUN", "C1 FAIL"), Gate("C3", "NOT_RUN", "C1 FAIL")])
        return _pack(rows, gates, "FAIL", "CLOCK", n_b1)
    gates.append(Gate("C1", "PASS", "strict leftover complete < T_LTF_B1; HTF BSP absent"))

    with_hist = {r["LTF_B1"] for r in rows if not r.get("NO_HIST_ANCHOR")}
    n_none = n_b1 - len(with_hist)
    if not with_hist:
        gates.append(Gate("C2", "FAIL", f"NO_HIST_ANCHOR={n_none}/{n_b1}"))
        gates.append(Gate("C3", "NOT_RUN", "C2 FAIL"))
        return _pack(rows, gates, "FAIL", "NO_HIST_ANCHOR", n_b1)
    gates.append(Gate("C2", "PASS", f"B1 with hist zs={len(with_hist)}/{n_b1}  NO_HIST_ANCHOR={n_none}"))

    hist_rows = [r for r in rows if not r.get("NO_HIST_ANCHOR")]
    n_zg_bad = sum(r.get("zg_unchanged") is False for r in hist_rows)
    n_zd_bad = sum(r.get("zd_unchanged") is False for r in hist_rows)
    n_gg_bad = sum(r.get("gg_unchanged") is False for r in hist_rows)
    n_dd_bad = sum(r.get("dd_unchanged") is False for r in hist_rows)
    sides = []
    for r in hist_rows:
        for k in ("side_zg", "side_zd", "side_gg", "side_dd"):
            if r.get(k) is not None:
                sides.append(r[k])
    if any(s not in {"ABOVE", "CONTACT", "BELOW"} for s in sides):
        gates.append(Gate("C3", "FAIL", "unbucketed rail"))
        return _pack(rows, gates, "FAIL", "CLOCK", n_b1)
    cnt = Counter(sides)
    gates.append(
        Gate(
            "C3",
            "PASS",
            f"rails={len(sides)} ABOVE={cnt['ABOVE']} CONTACT={cnt['CONTACT']} BELOW={cnt['BELOW']} "
            f"zg_rewrite={n_zg_bad} zd_rewrite={n_zd_bad} gg_rewrite={n_gg_bad} dd_rewrite={n_dd_bad}",
        )
    )
    kind = "HIST_ANCHOR_EXISTS"
    return _pack(rows, gates, "PASS", kind, n_b1)


def _pack(rows, gates, decision, kind, n_b1) -> dict:
    hist_rows = [r for r in rows if not r.get("NO_HIST_ANCHOR")]
    with_hist = {r["LTF_B1"] for r in hist_rows}
    per_b1 = {}
    for r in hist_rows:
        per_b1[r["LTF_B1"]] = r.get("n_hist_zs") or per_b1.get(r["LTF_B1"], 0)
    sides = Counter()
    for r in hist_rows:
        for k in ("side_zg", "side_zd", "side_gg", "side_dd"):
            if r.get(k):
                sides[(k.replace("side_", ""), r[k])] += 1
    rail_tbl = {f"{rail}_{side}": sides.get((rail, side), 0) for rail in ("zg", "zd", "gg", "dd") for side in ("ABOVE", "CONTACT", "BELOW")}
    summary = {
        "n_ltf_b1": n_b1,
        "n_b1_with_hist": len(with_hist),
        "n_no_hist_anchor": n_b1 - len(with_hist),
        "n_hist_zs_rows": len(hist_rows),
        "hist_zs_per_b1": per_b1,
        "rails": rail_tbl,
        "n_zg_rewrite": sum(r.get("zg_unchanged") is False for r in hist_rows),
        "n_gg_rewrite": sum(r.get("gg_unchanged") is False for r in hist_rows),
    }
    return {
        "experiment": "CHAN_HTF_HIST_ANCHOR_LTF_B1_001",
        "phase": "0",
        "decision": decision,
        "kind": kind,
        "n_events": len(rows),
        "gates": [asdict(g) for g in gates],
        "summary": summary,
        "blocked": "Q4 B1→B2=BLOCKED OF=BLOCKED SMC=BLOCKED MACD=BLOCKED HTF_BSP=FORBIDDEN living盒=NOT_OBJECT Entry=FORBIDDEN",
    }
