"""Phase 0: T0 causal → F1 kline align → F2 independent dimension → F3 identity."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from chan_fractal_of.clock import ClockState
from chan_fractal_of.of_window import snapshots_for_event
from chan_trade_of.frozen_config import (
    F1_MED_REL_MAX,
    F1_SPEARMAN_MIN,
    F2_REWRITE_RHO,
    F2_WITHIN_CV_MIN,
    assert_clean,
)
from chan_trade_of.trades import TradeStore, forming_snap


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 5 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(pd.Series(a).corr(pd.Series(b), method="spearman"))


def _ols_r2(y: np.ndarray, X: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    m = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[m], X[m]
    if len(y) < 10 or np.std(y) == 0:
        return float("nan")
    A = np.column_stack([np.ones(len(y)), X])
    try:
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    except np.linalg.LinAlgError:
        return float("nan")
    pred = A @ coef
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def _cv(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return float("nan")
    mu = float(np.mean(x))
    if mu == 0:
        return float("nan")
    return float(np.std(x) / abs(mu))


def audit(state: ClockState, of_1m: pd.DataFrame, trades: TradeStore) -> dict:
    rows = []
    leak = 0
    n_empty = 0
    for ev in state.events:
        k = snapshots_for_event(ev, of_1m)["forming"]
        t = forming_snap(ev, trades)
        leak += t.leak
        if t.n == 0:
            n_empty += 1
        rec = {
            "fx_id": ev.fx_id,
            "fx_side": ev.fx_side,
            "retracted": ev.retracted,
            "T_FX_VISIBLE": str(ev.T_FX_VISIBLE),
            "mid_range": ev.mid_range,
            "kline_delta": k.of_delta,
            "kline_volume": k.of_volume,
            "trade_n": t.n,
            "trade_delta": t.delta,
            "trade_volume": t.volume,
            "hhi": t.hhi,
            "n_levels": t.n_levels,
            "speed": t.speed,
            "push": t.push,
            "duration_s": t.duration_s,
            "leak": t.leak,
        }
        assert_clean(rec)
        rows.append(rec)

    gates: list[Gate] = []
    n = len(rows)
    n_retract = sum(1 for r in rows if r["retracted"])
    if leak != 0:
        gates.append(Gate("T0", "FAIL", f"future trade leak={leak}"))
    elif n == 0:
        gates.append(Gate("T0", "FAIL", "no fractals"))
    else:
        gates.append(Gate("T0", "PASS", f"n_fx={n} empty={n_empty} leak=0 retracted={n_retract}"))

    if gates[-1].verdict != "PASS":
        gates.extend(
            [
                Gate("F1", "NOT_RUN", "T0 FAIL"),
                Gate("F2", "NOT_RUN", "T0 FAIL"),
                Gate("F3", "NOT_RUN", "T0 FAIL"),
            ]
        )
        return _pack(state, rows, gates, "FAIL", "CLOCK")

    d_k = np.array([r["kline_delta"] for r in rows], dtype=float)
    d_t = np.array([r["trade_delta"] for r in rows], dtype=float)
    rho = _corr(d_k, d_t)
    rel = np.abs(d_t - d_k) / np.maximum(np.abs(d_k), 1e-6)
    med_rel = float(np.median(rel[np.isfinite(rel)])) if np.isfinite(rel).any() else float("nan")
    if not np.isfinite(rho) or rho < F1_SPEARMAN_MIN or med_rel > F1_MED_REL_MAX:
        gates.append(Gate("F1", "FAIL", f"spearman={rho:.4f} med_rel={med_rel:.4g} (need ≥{F1_SPEARMAN_MIN} / ≤{F1_MED_REL_MAX})"))
    else:
        gates.append(Gate("F1", "PASS", f"spearman={rho:.4f} med_rel={med_rel:.4g}"))

    if gates[-1].verdict != "PASS":
        gates.extend([Gate("F2", "NOT_RUN", "F1 FAIL"), Gate("F3", "NOT_RUN", "F1 FAIL")])
        return _pack(state, rows, gates, "FAIL", "ALIGN")

    vol = np.array([r["kline_volume"] for r in rows], dtype=float)
    rng = np.array([r["mid_range"] for r in rows], dtype=float)
    plane = np.column_stack([np.abs(d_k), vol, rng])
    feats = {
        "hhi": np.array([r["hhi"] for r in rows], dtype=float),
        "speed": np.array([r["speed"] for r in rows], dtype=float),
        "push": np.array([r["push"] for r in rows], dtype=float),
    }
    rho_max: dict[str, float] = {}
    r2: dict[str, float] = {}
    independent: list[str] = []
    for name, y in feats.items():
        rhos = [abs(_corr(y, plane[:, j])) for j in range(3)]
        rho_max[name] = float(np.nanmax(rhos)) if rhos else float("nan")
        r2[name] = _ols_r2(y, plane)
        if rho_max[name] < F2_REWRITE_RHO:
            independent.append(name)

    # same volume + similar range: middle 60% volume × middle 60% range
    v_lo, v_hi = np.nanpercentile(vol, [20, 80])
    r_lo, r_hi = np.nanpercentile(rng, [20, 80])
    mask = (vol >= v_lo) & (vol <= v_hi) & (rng >= r_lo) & (rng <= r_hi)
    within_cv = {k: _cv(v[mask]) for k, v in feats.items()}
    spread_ok = [k for k, c in within_cv.items() if np.isfinite(c) and c >= F2_WITHIN_CV_MIN]
    new_dim = sorted(set(independent) & set(spread_ok))

    detail = (
        f"rho_max={{{', '.join(f'{k}={v:.3f}' for k,v in rho_max.items())}}} "
        f"R2={{{', '.join(f'{k}={v:.3f}' for k,v in r2.items())}}} "
        f"within_cv={{{', '.join(f'{k}={v:.3f}' for k,v in within_cv.items())}}} "
        f"n_matched={int(mask.sum())}"
    )
    if not new_dim:
        gates.append(
            Gate(
                "F2",
                "FAIL",
                "no independent dimension vs delta+volume+range  " + detail,
            )
        )
        kind = "NO_NEW_INFO"
        decision = "FAIL"
    else:
        gates.append(Gate("F2", "PASS", f"new_dim={new_dim}  " + detail))
        kind = "NEW_DIMENSION"
        decision = "PASS"

    if n_retract != 0:
        gates.append(Gate("F3", "FAIL", f"retracted={n_retract}"))
        if decision == "PASS":
            decision, kind = "FAIL", "IDENTITY"
    else:
        gates.append(Gate("F3", "PASS", "retracted=0 forming clipped at T_FX_VISIBLE"))

    if gates[-1].verdict != "PASS" and decision == "PASS":
        decision, kind = "FAIL", "IDENTITY"

    return _pack(state, rows, gates, decision, kind)


def _pack(state: ClockState, rows: list, gates: list[Gate], decision: str, kind: str) -> dict:
    blocked = "5m=BLOCKED L2=BLOCKED absorption=NOT_A_DETECTOR B1/B2=FORBIDDEN HTF=BLOCKED SMC=BLOCKED"
    if decision == "FAIL" and kind == "NO_NEW_INFO":
        blocked += "  aggTrades finer but no new information in this window"
    return {
        "experiment": "CHAN_TRADE_OF_001",
        "decision": decision,
        "kind": kind,
        "n_15m": state.n_15m,
        "n_klc": state.n_klc,
        "n_events": len(rows),
        "gates": [g.__dict__ for g in gates],
        "summary": _summary(rows) if rows else {},
        "blocked": blocked,
        "events": rows,
    }


def _summary(rows: list) -> dict:
    def arr(k):
        return np.array([r[k] for r in rows], dtype=float)

    out = {}
    for k in ("kline_delta", "trade_delta", "kline_volume", "trade_volume", "hhi", "speed", "push", "mid_range"):
        x = arr(k)
        x = x[np.isfinite(x)]
        if len(x) == 0:
            continue
        out[f"{k}_p50"] = float(np.median(x))
        out[f"{k}_p10"] = float(np.percentile(x, 10))
        out[f"{k}_p90"] = float(np.percentile(x, 90))
    return out
