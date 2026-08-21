"""Phase 0: prior space / stability / spatial landing. No B1→B2. No OF/SMC."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

import numpy as np

from chan_htf_zs_ltf_b1.frozen_config import P0_MIN_B1, assert_clean
from chan_htf_zs_ltf_b1.phase0_schema import assert_no_htf_bsp


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def audit_phase0(rows: list[dict]) -> dict:
    for r in rows:
        assert_clean(r)
        assert_no_htf_bsp(r)
    gates: list[Gate] = []
    n = len(rows)
    if n < P0_MIN_B1:
        gates.append(Gate("C0", "FAIL", f"n_LTF_B1={n} min={P0_MIN_B1}"))
        for name in ("C1", "C2", "C3", "C4"):
            gates.append(Gate(name, "NOT_RUN", "C0 FAIL"))
        return _pack(rows, gates, "FAIL", "CLOCK")

    gates.append(Gate("C0", "PASS", f"n_LTF_B1={n}"))

    future = 0
    for r in rows:
        vis = r.get("T_HTF_ZS_VISIBLE")
        t1 = r.get("T_LTF_B1")
        if vis is not None and t1 is not None and vis >= t1:
            future += 1
    if future:
        gates.append(Gate("C1", "FAIL", f"T_HTF_ZS_VISIBLE >= T_LTF_B1 on {future} rows"))
        gates.extend([Gate("C2", "NOT_RUN", "C1 FAIL"), Gate("C3", "NOT_RUN", "C1 FAIL"), Gate("C4", "NOT_RUN", "C1 FAIL")])
        return _pack(rows, gates, "FAIL", "CLOCK")
    gates.append(Gate("C1", "PASS", "strict T_HTF_ZS_VISIBLE < T_LTF_B1; HTF BSP absent"))

    n_rewrite = sum(int(r.get("n_htf_rewrite_at_b1") or 0) > 0 for r in rows)
    if n_rewrite:
        gates.append(Gate("C2", "FAIL", f"zg/zd rewrite at B1 on {n_rewrite}/{n} rows"))
        gates.extend([Gate("C3", "NOT_RUN", "C2 FAIL"), Gate("C4", "NOT_RUN", "C2 FAIL")])
        return _pack(rows, gates, "FAIL", "UNSTABLE")
    gates.append(Gate("C2", "PASS", "zg/zd unchanged vs visibility on all B1 snapshots"))

    valid = [r for r in rows if r.get("ZS_valid_at_B1") and not r.get("NO_HTF_ZS")]
    n_none = sum(1 for r in rows if r.get("NO_HTF_ZS"))
    if not valid:
        gates.append(Gate("C3", "FAIL", f"no prior living HTF ZS  NO_HTF_ZS={n_none}/{n}"))
        gates.append(Gate("C4", "NOT_RUN", "C3 FAIL"))
        return _pack(rows, gates, "FAIL", "NO_PRIOR_SPACE")
    gates.append(Gate("C3", "PASS", f"prior living HTF ZS on {len(valid)}/{n}  NO_HTF_ZS={n_none}"))

    buckets = Counter(r.get("spatial_bucket") for r in valid)
    if any(r.get("spatial_bucket") not in {"INSIDE", "BOUNDARY_CONTACT", "OUTSIDE"} for r in valid):
        gates.append(Gate("C4", "FAIL", f"unbucketed valid rows {dict(buckets)}"))
        return _pack(rows, gates, "FAIL", "NO_PRIOR_SPACE")
    gates.append(
        Gate(
            "C4",
            "PASS",
            " ".join(f"{k}={buckets.get(k, 0)}" for k in ("INSIDE", "BOUNDARY_CONTACT", "OUTSIDE")),
        )
    )
    return _pack(rows, gates, "PASS", "SPACE_OBJECT_EXISTS")


def _pack(rows, gates, decision, kind) -> dict:
    valid = [r for r in rows if r.get("ZS_valid_at_B1") and not r.get("NO_HTF_ZS")]
    dts = [r["delta_t"] for r in valid if r.get("delta_t") is not None]
    summary = {
        "n_ltf_b1": len(rows),
        "n_prior_valid": len(valid),
        "n_no_htf_zs": sum(1 for r in rows if r.get("NO_HTF_ZS")),
        "n_leftover": sum(1 for r in rows if r.get("zs_leftover_at_b1")),
        "buckets": dict(Counter(r.get("spatial_bucket") for r in valid)),
        "delta_t_hours_p50": float(np.median(dts) / 3600.0) if dts else float("nan"),
        "delta_t_hours_min": float(min(dts) / 3600.0) if dts else float("nan"),
        "delta_t_hours_max": float(max(dts) / 3600.0) if dts else float("nan"),
    }
    return {
        "experiment": "CHAN_HTF_ZS_LTF_B1_001",
        "phase": "0",
        "decision": decision,
        "kind": kind,
        "n_events": len(rows),
        "gates": [asdict(g) for g in gates],
        "summary": summary,
        "blocked": "Phase2 B1→B2=BLOCKED OF=BLOCKED SMC=BLOCKED HTF_BSP=FORBIDDEN Entry=FORBIDDEN 5m=BLOCKED",
    }
