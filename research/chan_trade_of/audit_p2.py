"""Phase 2: mechanism vs artifact. 15m same events. No B1/B2. No absorption name."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from chan_trade_of.audit_p1 import _corr, _resid
from chan_trade_of.frozen_config import (
    P2_ARTIFACT_FLOOR,
    P2_EXTREME_P,
    P2_MIN_N,
    P2_N_BINS,
    P2_SIGN,
    P2_SLICE_RHO,
    assert_clean,
)


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def _ok_slice(rho: float, n: int) -> bool:
    if n < P2_MIN_N or not np.isfinite(rho):
        return False
    return np.sign(rho) == P2_SIGN and abs(rho) >= P2_SLICE_RHO


def audit_phase2(rows: list[dict]) -> dict:
    for r in rows:
        assert_clean(r)
    n = len(rows)
    leak = sum(int(r.get("leak") or 0) for r in rows)
    gates: list[Gate] = []
    if leak or n == 0:
        gates.append(Gate("M0", "FAIL", f"leak={leak} n={n}"))
        for name in ("M1", "M2", "M3", "M4"):
            gates.append(Gate(name, "NOT_RUN", "M0 FAIL"))
        return _pack(n, gates, "FAIL", "CLOCK")

    hhi = np.array([r["hhi"] for r in rows], dtype=float)
    push = np.array([r["push"] for r in rows], dtype=float)
    vol = np.array([r["kline_volume"] for r in rows], dtype=float)
    dlt = np.abs(np.array([r["kline_delta"] for r in rows], dtype=float))
    nlev = np.array([r["n_levels"] for r in rows], dtype=float)
    rng = np.array([r["mid_range"] for r in rows], dtype=float)
    side = np.array([r["fx_side"] for r in rows])
    tvis = pd.to_datetime([r["T_FX_VISIBLE"] for r in rows], utc=True).asi8.astype(float)
    inv_n = 1.0 / np.maximum(nlev, 1.0)
    effort = dlt / np.maximum(vol, 1e-9)
    plane = np.column_stack([dlt, vol])
    hhi_r = _resid(hhi, plane)
    push_r = _resid(push, plane)
    rho0 = _corr(hhi_r, push_r)
    gates.append(Gate("M0", "PASS", f"n={n} leak=0 rho_resid={rho0:.3f} (Phase 1 control)"))

    tq = pd.qcut(tvis, P2_N_BINS, labels=False, duplicates="drop") + 1
    time_rhos = []
    for b in range(1, P2_N_BINS + 1):
        m = tq == b
        time_rhos.append((_corr(hhi_r[m], push_r[m]), int(m.sum())))
    t_ok = all(_ok_slice(r, k) for r, k in time_rhos)
    gates.append(
        Gate(
            "M1",
            "PASS" if t_ok else "FAIL",
            "time terciles " + " ".join(f"ρ={r:.3f} n={k}" for r, k in time_rhos),
        )
    )

    bot = side == "BOTTOM"
    top = side == "TOP"
    rho_bot = _corr(hhi_r[bot], push_r[bot])
    rho_top = _corr(hhi_r[top], push_r[top])
    d_ok = _ok_slice(rho_bot, int(bot.sum())) and _ok_slice(rho_top, int(top.sum()))
    gates.append(
        Gate("M2", "PASS" if d_ok else "FAIL", f"bottom ρ={rho_bot:.3f} n={int(bot.sum())}  top ρ={rho_top:.3f} n={int(top.sum())}")
    )

    eq = pd.qcut(effort, P2_N_BINS, labels=False, duplicates="drop") + 1
    eff_rhos = []
    for b in range(1, P2_N_BINS + 1):
        m = eq == b
        eff_rhos.append((_corr(hhi_r[m], push_r[m]), int(m.sum())))
    e_ok = all(_ok_slice(r, k) for r, k in eff_rhos)
    gates.append(
        Gate(
            "M3",
            "PASS" if e_ok else "FAIL",
            "effort terciles |delta|/vol " + " ".join(f"ρ={r:.3f} n={k}" for r, k in eff_rhos),
        )
    )

    # Alternative explanations — must not eat the residual link.
    plane_tick = np.column_stack([dlt, vol, rng, inv_n])
    rho_tick = _corr(_resid(hhi, plane_tick), _resid(push, plane_tick))
    rho_hhi_invn = _corr(hhi, inv_n)
    cap_d = np.nanpercentile(dlt, P2_EXTREME_P)
    cap_r = np.nanpercentile(rng, P2_EXTREME_P)
    keep = (dlt <= cap_d) & (rng <= cap_r)
    rho_ex = _corr(hhi_r[keep], push_r[keep])
    tick_ok = np.isfinite(rho_tick) and np.sign(rho_tick) == P2_SIGN and abs(rho_tick) >= P2_ARTIFACT_FLOOR
    ext_ok = np.isfinite(rho_ex) and np.sign(rho_ex) == P2_SIGN and abs(rho_ex) >= P2_ARTIFACT_FLOOR
    a_ok = tick_ok and ext_ok
    gates.append(
        Gate(
            "M4",
            "PASS" if a_ok else "FAIL",
            f"resid+|range+1/n_levels ρ={rho_tick:.3f}  drop_p{P2_EXTREME_P} ρ={rho_ex:.3f} n={int(keep.sum())}  Spearman(HHI,1/n_levels)={rho_hhi_invn:.3f}",
        )
    )

    m123 = t_ok and d_ok and e_ok
    if not a_ok:
        decision, kind = "FAIL", "ARTIFACT"
    elif m123:
        decision, kind = "PASS", "MECHANISM_STABLE"
    else:
        decision, kind = "FAIL", "CONDITIONAL_MECHANISM"

    summary = {
        "rho_resid": rho0,
        "time": [{"rho": r, "n": k} for r, k in time_rhos],
        "bottom": rho_bot,
        "top": rho_top,
        "effort": [{"rho": r, "n": k} for r, k in eff_rhos],
        "rho_after_range_nlevels": rho_tick,
        "rho_drop_extremes": rho_ex,
        "spearman_hhi_inv_nlevels": rho_hhi_invn,
        "n_drop_keep": int(keep.sum()),
    }
    blocked = "≠NEW_EDGE 不准 B1/B2 HTF SMC 5m absorption 交易层"
    return {
        "experiment": "CHAN_TRADE_OF_001",
        "phase": "2",
        "decision": decision,
        "kind": kind,
        "n_events": n,
        "gates": [g.__dict__ for g in gates],
        "summary": summary,
        "blocked": blocked,
    }


def _pack(n, gates, decision, kind) -> dict:
    return {
        "experiment": "CHAN_TRADE_OF_001",
        "phase": "2",
        "decision": decision,
        "kind": kind,
        "n_events": n,
        "gates": [g.__dict__ for g in gates],
        "summary": {},
        "blocked": "≠NEW_EDGE 不准 B1/B2 HTF SMC 5m absorption 交易层",
    }
