"""Phase 1: residual HHI → push. 15m only. No absorption. No quintile hunt."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from chan_trade_of.frozen_config import (
    P1_MIN_AGREE,
    P1_MIN_CELL,
    P1_N_BINS,
    P1_RHO_STABLE,
    assert_clean,
)


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    if len(a) < 8 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(pd.Series(a).corr(pd.Series(b), method="spearman"))


def _resid(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    m = np.isfinite(y) & np.isfinite(X).all(axis=1)
    out = np.full_like(y, np.nan, dtype=float)
    if m.sum() < 10:
        return out
    A = np.column_stack([np.ones(int(m.sum())), X[m]])
    coef, *_ = np.linalg.lstsq(A, y[m], rcond=None)
    out[m] = y[m] - A @ coef
    return out


def _inc_r2(y: np.ndarray, X0: np.ndarray, x_add: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    X0 = np.asarray(X0, dtype=float)
    x_add = np.asarray(x_add, dtype=float)
    m = np.isfinite(y) & np.isfinite(X0).all(axis=1) & np.isfinite(x_add)
    if m.sum() < 15 or np.std(y[m]) == 0:
        return float("nan")

    def r2(A, yy):
        c, *_ = np.linalg.lstsq(A, yy, rcond=None)
        pred = A @ c
        ss_res = float(np.sum((yy - pred) ** 2))
        ss_tot = float(np.sum((yy - yy.mean()) ** 2))
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    yy = y[m]
    A0 = np.column_stack([np.ones(int(m.sum())), X0[m]])
    A1 = np.column_stack([A0, x_add[m]])
    return float(r2(A1, yy) - r2(A0, yy))


def audit_phase1(rows: list[dict]) -> dict:
    for r in rows:
        assert_clean(r)
    n = len(rows)
    leak = sum(int(r.get("leak") or 0) for r in rows)
    gates: list[Gate] = []
    if leak != 0 or n == 0:
        gates.append(Gate("C1", "FAIL", f"leak={leak} n={n}"))
        gates.extend(
            [
                Gate("C2", "NOT_RUN", "C1 FAIL"),
                Gate("C3", "NOT_RUN", "C1 FAIL"),
                Gate("C4", "NOT_RUN", "C1 FAIL"),
                Gate("C5", "NOT_RUN", "C1 FAIL"),
            ]
        )
        return _pack(rows, gates, "FAIL", "CLOCK")
    gates.append(Gate("C1", "PASS", f"n={n} leak=0 t<T_FX_VISIBLE"))

    hhi = np.array([r["hhi"] for r in rows], dtype=float)
    push = np.array([r["push"] for r in rows], dtype=float)
    vol = np.array([r["kline_volume"] for r in rows], dtype=float)
    dlt = np.abs(np.array([r["kline_delta"] for r in rows], dtype=float))
    side = np.array([r["fx_side"] for r in rows])
    tvis = pd.to_datetime([r["T_FX_VISIBLE"] for r in rows], utc=True)

    plane = np.column_stack([dlt, vol])
    hhi_r = _resid(hhi, plane)
    push_r = _resid(push, plane)
    rho_raw = _corr(hhi, push)
    rho_res = _corr(hhi_r, push_r)
    inc = _inc_r2(push, plane, hhi)

    try:
        vq = pd.qcut(vol, P1_N_BINS, labels=False, duplicates="drop") + 1
        dq = pd.qcut(dlt, P1_N_BINS, labels=False, duplicates="drop") + 1
    except ValueError:
        gates.append(Gate("C2", "FAIL", "qcut collapsed"))
        gates.extend([Gate("C3", "NOT_RUN", "C2 FAIL"), Gate("C4", "NOT_RUN", "C2 FAIL"), Gate("C5", "NOT_RUN", "C2 FAIL")])
        return _pack(rows, gates, "FAIL", "CONDITION")

    cells = []
    for vi in range(1, P1_N_BINS + 1):
        for di in range(1, P1_N_BINS + 1):
            m = (vq == vi) & (dq == di)
            nn = int(m.sum())
            rho = _corr(hhi[m], push[m]) if nn else float("nan")
            cells.append({"v": int(vi), "d": int(di), "n": nn, "rho": rho})

    n_ok = sum(1 for c in cells if c["n"] >= P1_MIN_CELL)
    if n_ok < P1_MIN_AGREE:
        gates.append(Gate("C2", "FAIL", f"cells_n>={P1_MIN_CELL}: {n_ok} < {P1_MIN_AGREE}"))
    else:
        gates.append(Gate("C2", "PASS", f"3×3 |delta|×volume  cells_ge_{P1_MIN_CELL}={n_ok}"))

    if gates[-1].verdict != "PASS":
        gates.extend([Gate("C3", "NOT_RUN", "C2 FAIL"), Gate("C4", "NOT_RUN", "C2 FAIL"), Gate("C5", "NOT_RUN", "C2 FAIL")])
        return _pack(rows, gates, "FAIL", "CONDITION", cells, rho_raw, rho_res, inc)

    eligible = [c for c in cells if c["n"] >= P1_MIN_CELL and np.isfinite(c["rho"])]
    if not np.isfinite(rho_res):
        gates.append(Gate("C3", "FAIL", "residual Spearman undefined"))
        gates.extend([Gate("C4", "NOT_RUN", "C3 FAIL"), Gate("C5", "NOT_RUN", "C3 FAIL")])
        return _pack(rows, gates, "FAIL", "NO_RELATION", cells, rho_raw, rho_res, inc)

    sign = np.sign(rho_res) if rho_res != 0 else 0.0
    n_agree = sum(1 for c in eligible if np.sign(c["rho"]) == sign)
    cell_txt = " ".join(f"V{c['v']}D{c['d']}:n={c['n']} ρ={c['rho']:.3f}" for c in cells)
    gates.append(
        Gate(
            "C3",
            "PASS" if abs(rho_res) >= P1_RHO_STABLE else "WEAK",
            f"rho_raw={rho_raw:.3f} rho_resid={rho_res:.3f} inc_R2={inc:.4f}  {cell_txt}",
        )
    )

    agree_ok = n_agree >= P1_MIN_AGREE
    gates.append(
        Gate(
            "C4",
            "PASS" if agree_ok else "FAIL",
            f"same_sign_as_resid {n_agree}/{len(eligible)} eligible cells (need {P1_MIN_AGREE})",
        )
    )

    mid = tvis.min() + (tvis.max() - tvis.min()) / 2
    rho_a = _corr(hhi_r[tvis < mid], push_r[tvis < mid])
    rho_b = _corr(hhi_r[tvis >= mid], push_r[tvis >= mid])
    rho_bot = _corr(hhi_r[side == "BOTTOM"], push_r[side == "BOTTOM"])
    rho_top = _corr(hhi_r[side == "TOP"], push_r[side == "TOP"])
    halves_ok = (
        np.isfinite(rho_a)
        and np.isfinite(rho_b)
        and np.sign(rho_a) == sign
        and np.sign(rho_b) == sign
        and abs(rho_a) >= P1_RHO_STABLE / 2
        and abs(rho_b) >= P1_RHO_STABLE / 2
    )
    sides_ok = (
        np.isfinite(rho_bot)
        and np.isfinite(rho_top)
        and np.sign(rho_bot) == sign
        and np.sign(rho_top) == sign
    )
    gates.append(
        Gate(
            "C5",
            "PASS" if halves_ok and sides_ok else "FAIL",
            f"halfA={rho_a:.3f} halfB={rho_b:.3f} bottom={rho_bot:.3f} top={rho_top:.3f}",
        )
    )

    strong = abs(rho_res) >= P1_RHO_STABLE
    c3_ok = strong
    c4_ok = agree_ok
    c5_ok = halves_ok and sides_ok
    if c3_ok and c4_ok and c5_ok:
        decision, kind = "PASS", "NEW_DIMENSION_CONFIRMED"
    elif strong and (c4_ok or c5_ok):
        decision, kind = "PASS", "CONDITIONAL_DIMENSION"
    elif strong:
        decision, kind = "FAIL", "UNSTABLE"
    else:
        decision, kind = "FAIL", "NO_STRUCTURE"

    # C3 WEAK is not a hard stop; kind already encodes it
    if gates[2].verdict == "WEAK":
        gates[2] = Gate("C3", "FAIL", gates[2].detail)

    summary = {
        "rho_raw": rho_raw,
        "rho_resid": rho_res,
        "inc_R2": inc,
        "n_agree_cells": n_agree,
        "n_eligible_cells": len(eligible),
        "rho_half_a": rho_a,
        "rho_half_b": rho_b,
        "rho_bottom": rho_bot,
        "rho_top": rho_top,
        "cells": cells,
    }
    return _pack(rows, gates, decision, kind, cells, rho_raw, rho_res, inc, summary)


def _pack(
    rows,
    gates,
    decision,
    kind,
    cells=None,
    rho_raw=None,
    rho_res=None,
    inc=None,
    summary=None,
) -> dict:
    blocked = "NEW_DIMENSION≠NEW_EDGE 5m=BLOCKED absorption=NOT_A_DETECTOR B1/B2=FORBIDDEN HTF=BLOCKED SMC=BLOCKED no_threshold no_backtest"
    return {
        "experiment": "CHAN_TRADE_OF_001",
        "phase": "1",
        "decision": decision,
        "kind": kind,
        "n_events": len(rows),
        "gates": [g.__dict__ for g in gates],
        "summary": summary or {},
        "blocked": blocked,
        "rho_raw": rho_raw,
        "rho_resid": rho_res,
        "inc_R2": inc,
        "cells": cells or [],
    }
