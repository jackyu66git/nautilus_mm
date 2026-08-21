"""A1 → A2 → A3. Earlier FAIL stops later gates."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from chan_fractal_of.clock import ClockState, FractalEvent
from chan_fractal_of.frozen_config import assert_phase_a_clean
from chan_fractal_of.of_window import OfSnapshot, snapshots_for_event


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 5:
        return float("nan")
    if np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(pd.Series(a).corr(pd.Series(b), method="spearman"))


def audit(state: ClockState, of: pd.DataFrame) -> dict:
    rows = []
    leak_total = 0
    for ev in state.events:
        snaps = snapshots_for_event(ev, of)
        rec = {
            "fx_id": ev.fx_id,
            "fx_side": ev.fx_side,
            "T_FX_VISIBLE": str(ev.T_FX_VISIBLE),
            "forming_ts": str(ev.forming_ts) if ev.forming_ts is not None else None,
            "candidate_ts": str(ev.candidate_ts) if ev.candidate_ts is not None else None,
            "confirmed_ts": str(ev.confirmed_ts) if ev.confirmed_ts is not None else None,
            "retracted": ev.retracted,
            "mid_range": ev.mid_range,
            "of_n_forming": snaps["forming"].n_1m,
            "of_n_visible": snaps["visible"].n_1m,
            "of_delta_forming": snaps["forming"].of_delta,
            "of_delta_visible": snaps["visible"].of_delta,
            "of_imbalance_forming": snaps["forming"].of_imbalance,
            "of_imbalance_visible": snaps["visible"].of_imbalance,
            "of_volume_forming": snaps["forming"].of_volume,
            "of_volume_visible": snaps["visible"].of_volume,
            "leak": snaps["forming"].future_leak + snaps["visible"].future_leak,
        }
        assert_phase_a_clean(rec)
        leak_total += rec["leak"]
        rows.append(rec)

    n = len(rows)
    n_bottom = sum(1 for r in rows if r["fx_side"] == "BOTTOM")
    n_top = n - n_bottom
    n_retract = sum(1 for r in rows if r["retracted"])
    n_form_empty = sum(1 for r in rows if r["of_n_forming"] == 0)
    n_vis_empty = sum(1 for r in rows if r["of_n_visible"] == 0)
    n_rewrite = sum(1 for r in rows if r["of_n_forming"] == 0 and r["of_n_visible"] > 0)

    gates: list[Gate] = []

    # A1
    if leak_total != 0:
        gates.append(Gate("A1", "FAIL", f"future OF leak={leak_total}"))
    elif n == 0:
        gates.append(Gate("A1", "FAIL", "no fractals"))
    else:
        gates.append(Gate("A1", "PASS", f"n_fx={n} bottom={n_bottom} top={n_top} leak=0"))

    a1 = gates[-1].verdict
    if a1 != "PASS":
        gates.append(Gate("A2", "NOT_RUN", "A1 FAIL"))
        gates.append(Gate("A3", "NOT_RUN", "A1 FAIL"))
        return _pack(state, rows, gates, "FAIL")

    # A2
    delta = np.array([r["of_delta_forming"] for r in rows], dtype=float)
    imb = np.array([r["of_imbalance_forming"] for r in rows], dtype=float)
    rng = np.array([r["mid_range"] for r in rows], dtype=float)
    signed_rng = np.array(
        [r["mid_range"] if r["fx_side"] == "TOP" else -r["mid_range"] for r in rows],
        dtype=float,
    )
    std_d = float(np.std(delta))
    std_i = float(np.std(imb))
    c_d = _corr(delta, signed_rng)
    c_i = _corr(imb, signed_rng)
    if n_form_empty == n:
        gates.append(Gate("A2", "FAIL", "all forming OF windows empty"))
    elif std_d == 0.0 and std_i == 0.0:
        gates.append(Gate("A2", "FAIL", "OF collapsed to a single point"))
    elif abs(c_d) > 0.9 and abs(c_i) > 0.9:
        gates.append(Gate("A2", "FAIL", f"same-root vs range spearman delta={c_d:.3f} imb={c_i:.3f}"))
    else:
        gates.append(
            Gate(
                "A2",
                "PASS_CANDIDATE",
                f"std_delta={std_d:.4g} std_imb={std_i:.4g} spearman_delta={c_d:.3f} spearman_imb={c_i:.3f}",
            )
        )

    a2 = gates[-1].verdict
    if a2 != "PASS_CANDIDATE":
        gates.append(Gate("A3", "NOT_RUN", "A2 FAIL"))
        return _pack(state, rows, gates, "FAIL")

    # A3
    if n_retract > 0:
        gates.append(Gate("A3", "FAIL", f"fx retracted={n_retract}"))
    elif n_rewrite / n > 0.5:
        gates.append(Gate("A3", "FAIL", f"forming empty / visible nonempty = {n_rewrite}/{n}"))
    else:
        gates.append(
            Gate(
                "A3",
                "PASS",
                f"retracted=0 rewrite={n_rewrite}/{n} confirmed={sum(1 for r in rows if r['confirmed_ts'])}",
            )
        )

    a3 = gates[-1].verdict
    decision = "PASS" if a3 == "PASS" else "FAIL"
    extra = {
        "n": n,
        "n_bottom": n_bottom,
        "n_top": n_top,
        "n_retract": n_retract,
        "n_form_empty": n_form_empty,
        "n_vis_empty": n_vis_empty,
        "n_rewrite": n_rewrite,
        "std_delta_forming": std_d,
        "std_imb_forming": std_i,
        "spearman_delta_range": c_d,
        "spearman_imb_range": c_i,
        "delta_p10": float(np.percentile(delta, 10)),
        "delta_p50": float(np.percentile(delta, 50)),
        "delta_p90": float(np.percentile(delta, 90)),
        "imb_p10": float(np.percentile(imb, 10)),
        "imb_p50": float(np.percentile(imb, 50)),
        "imb_p90": float(np.percentile(imb, 90)),
    }
    return _pack(state, rows, gates, decision, extra)


def _pack(state, rows, gates, decision, extra=None) -> dict:
    return {
        "experiment": "CHAN_FRACTAL_OF_001",
        "phase": "A",
        "decision": decision,
        "n_15m": state.n_15m,
        "n_klc": state.n_klc,
        "gates": [asdict(g) for g in gates],
        "summary": extra or {},
        "n_events": len(rows),
        "events": rows,
    }
