"""S0 Clock → S1 Size → S2 Monotone → S3 Amplitude. Bottoms first. No B1/B2."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from chan_bi_of_strata.endpoints import ConfirmedEndpoint
from chan_bi_of_strata.frozen_config import (
    HOLDS,
    MIN_PER_Q,
    N_QUINT,
    RHO_MONOTONE,
    assert_clean,
)
from chan_bi_of_strata.path import align_entry, path_stats
from chan_fractal_of.clock import ClockState, FractalEvent
from chan_fractal_of.of_window import snapshots_for_event


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def _pct(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "p10": float("nan"), "p50": float("nan"), "p90": float("nan")}
    return {
        "n": int(len(x)),
        "p10": float(np.percentile(x, 10)),
        "p50": float(np.percentile(x, 50)),
        "p90": float(np.percentile(x, 90)),
    }


def _median_spearman(medians: list[float]) -> float:
    y = np.array(medians, dtype=float)
    x = np.arange(1, len(y) + 1, dtype=float)
    if np.std(y) == 0 or np.any(~np.isfinite(y)):
        return float("nan")
    return float(pd.Series(x).corr(pd.Series(y), method="spearman"))


def _steps_ok(medians: list[float], decreasing: bool) -> int:
    ok = 0
    for a, b in zip(medians, medians[1:]):
        if decreasing and b <= a:
            ok += 1
        if not decreasing and b >= a:
            ok += 1
    return ok


def audit(
    state: ClockState,
    bar: pd.DataFrame,
    of: pd.DataFrame,
    ends: list[ConfirmedEndpoint],
    experiment: str = "CHAN_BI_OF_STRATA_001",
    scale: str = "15m bi-endpoint + 1m OF",
) -> dict:
    fx: dict[str, FractalEvent] = {e.fx_id: e for e in state.events}
    rows = []
    n_clock = 0
    leak_total = 0
    n_no_fx = 0
    n_short = 0

    for ep in ends:
        ev = fx.get(ep.fx_id)
        if ev is None:
            n_no_fx += 1
            continue
        if ev.fx_side != ep.side:
            n_clock += 1
            continue
        t_vis = pd.Timestamp(ev.T_FX_VISIBLE)
        if t_vis.tzinfo is None:
            t_vis = t_vis.tz_localize("UTC")
        if not (ep.T_BI_SURE > t_vis):
            n_clock += 1
            continue
        snaps = snapshots_for_event(ev, of)
        leak_total += snaps["forming"].future_leak
        entry_i = align_entry(bar, ep.T_BI_SURE)
        if entry_i is None:
            n_short += 1
            continue
        stats = path_stats(bar, entry_i, ep.side)
        if stats is None:
            n_short += 1
            continue
        rec = {
            "fx_id": ep.fx_id,
            "fx_side": ep.side,
            "T_FX_VISIBLE": str(t_vis),
            "T_BI_SURE": str(ep.T_BI_SURE),
            "mid_range": ev.mid_range,
            "of_delta_forming": snaps["forming"].of_delta,
            "of_imbalance_forming": snaps["forming"].of_imbalance,
            "of_n_forming": snaps["forming"].n_1m,
            "leak": snaps["forming"].future_leak,
            **stats,
        }
        assert_clean(rec)
        rows.append(rec)

    bottoms = [r for r in rows if r["fx_side"] == "BOTTOM"]
    gates: list[Gate] = []

    if leak_total != 0 or n_clock != 0:
        gates.append(Gate("S0", "FAIL", f"leak={leak_total} t_sure_not_after_fx={n_clock}"))
    else:
        gates.append(
            Gate(
                "S0",
                "PASS",
                f"leak=0 T_BI_SURE>T_FX_VISIBLE unmatched_fx={n_no_fx} truncated={n_short} n={len(rows)}",
            )
        )
    if gates[-1].verdict != "PASS":
        gates.extend([Gate("S1", "NOT_RUN", "S0 FAIL"), Gate("S2", "NOT_RUN", "S0 FAIL"), Gate("S3", "NOT_RUN", "S0 FAIL")])
        return _pack(state, rows, gates, "FAIL", "CLOCK", {}, experiment, scale)

    if len(bottoms) < N_QUINT * MIN_PER_Q:
        gates.append(Gate("S1", "FAIL", f"n_bottom_ep={len(bottoms)} < {N_QUINT * MIN_PER_Q}"))
    else:
        score = np.array([-r["of_delta_forming"] for r in bottoms], dtype=float)
        try:
            q = pd.qcut(score, N_QUINT, labels=False, duplicates="drop") + 1
        except ValueError:
            q = np.ones(len(bottoms), dtype=int)
        if int(pd.Series(q).nunique()) < N_QUINT:
            gates.append(Gate("S1", "FAIL", f"qcut collapsed nunique={int(pd.Series(q).nunique())}"))
        else:
            for r, qi in zip(bottoms, q):
                r["q"] = int(qi)
            counts = [sum(1 for r in bottoms if r["q"] == i) for i in range(1, N_QUINT + 1)]
            if min(counts) < MIN_PER_Q:
                gates.append(Gate("S1", "FAIL", f"per-q {counts} min={MIN_PER_Q}"))
            else:
                gates.append(Gate("S1", "PASS", f"n_bottom_ep={len(bottoms)} per_q={counts}"))

    if gates[-1].verdict != "PASS":
        gates.extend([Gate("S2", "NOT_RUN", "S1 FAIL"), Gate("S3", "NOT_RUN", "S1 FAIL")])
        return _pack(state, rows, gates, "FAIL", "SIZE", {}, experiment, scale)

    metrics = {
        "mae_16": ("mae_16", True),
        "mfe_16": ("mfe_16", False),
        **{f"ret_{n}": (f"ret_{n}", False) for n in HOLDS},
        **{f"ret_{n}_net": (f"ret_{n}_net", False) for n in HOLDS},
    }
    bucket = {}
    rho = {}
    steps = {}
    for name, (key, decr) in metrics.items():
        meds = []
        for i in range(1, N_QUINT + 1):
            vals = np.array([r[key] for r in bottoms if r["q"] == i], dtype=float)
            meds.append(float(np.median(vals)))
        bucket[name] = meds
        rho[name] = _median_spearman(meds)
        steps[name] = _steps_ok(meds, decreasing=decr)

    mae_ok = np.isfinite(rho["mae_16"]) and rho["mae_16"] <= -RHO_MONOTONE
    mfe_ok = np.isfinite(rho["mfe_16"]) and rho["mfe_16"] >= RHO_MONOTONE
    ret_ok = {n: np.isfinite(rho[f"ret_{n}"]) and rho[f"ret_{n}"] >= RHO_MONOTONE for n in HOLDS}
    net_ok = {n: np.isfinite(rho[f"ret_{n}_net"]) and rho[f"ret_{n}_net"] >= RHO_MONOTONE for n in HOLDS}
    any_ret = any(ret_ok.values())
    short_only = (ret_ok[4] or ret_ok[8]) and not ret_ok[16]
    fee_kills = any_ret and not any(net_ok.values())

    if mae_ok and any(net_ok.values()):
        kind = "STABLE_MONOTONE"
        s2 = "PASS"
        detail = "MAE gradient and fee-adjusted hold gradient"
    elif mae_ok and fee_kills:
        kind = "FEE_KILLS"
        s2 = "FAIL"
        detail = "MAE/gross hold gradient; fee-adjusted holds lose it"
    elif (mfe_ok or any_ret) and not mae_ok:
        kind = "MFE_ONLY"
        s2 = "FAIL"
        detail = "MFE/hold gradient without MAE improvement"
    elif short_only:
        kind = "SHORT_ONLY"
        s2 = "FAIL"
        detail = "short-hold gradient; 16-bar gone"
    else:
        kind = "NO_GRADIENT"
        s2 = "FAIL"
        detail = "no Q1→Q5 gradient"

    rho_txt = " ".join(f"{k}={v:.3f}" for k, v in rho.items())
    gates.append(Gate("S2", s2, f"{kind} {detail} rho[{rho_txt}] mae_steps={steps['mae_16']}/4"))

    extra = {
        "n_bottom_ep": len(bottoms),
        "per_q": [sum(1 for r in bottoms if r["q"] == i) for i in range(1, N_QUINT + 1)],
        "medians": bucket,
        "rho_median": rho,
        "concordant_steps": steps,
        "all_mae": _pct(np.array([r["mae_16"] for r in bottoms])),
        "all_mfe": _pct(np.array([r["mfe_16"] for r in bottoms])),
        "all_ret_16": _pct(np.array([r["ret_16"] for r in bottoms])),
        "all_ret_16_net": _pct(np.array([r["ret_16_net"] for r in bottoms])),
    }

    if s2 != "PASS":
        gates.append(Gate("S3", "NOT_RUN", "S2 FAIL"))
        return _pack(state, rows, gates, "FAIL", kind, extra, experiment, scale)

    # S3: MAE Q5 vs Q1 inside amplitude tertiles
    ranges = np.array([r["mid_range"] for r in bottoms], dtype=float)
    try:
        ac = pd.qcut(ranges, 3, labels=False, duplicates="drop")
    except ValueError:
        ac = np.zeros(len(bottoms), dtype=int)
    amp_bits = []
    survive = 0
    for b in sorted(set(int(x) for x in ac)):
        grp = [r for r, c in zip(bottoms, ac) if int(c) == b]
        q1 = [r["mae_16"] for r in grp if r["q"] == 1]
        q5 = [r["mae_16"] for r in grp if r["q"] == 5]
        if len(q1) < 8 or len(q5) < 8:
            amp_bits.append(f"amp{b}:n_q1={len(q1)} n_q5={len(q5)} SKIP")
            continue
        m1, m5 = float(np.median(q1)), float(np.median(q5))
        amp_bits.append(f"amp{b}:mae_q1={m1:.4g} mae_q5={m5:.4g}")
        if m5 < m1:
            survive += 1
    if survive < 1:
        gates.append(Gate("S3", "FAIL", f"MAE gradient not outside amplitude {'; '.join(amp_bits)}"))
        return _pack(state, rows, gates, "FAIL", "AMPLITUDE", extra, experiment, scale)
    gates.append(Gate("S3", "PASS", f"MAE Q5<Q1 in {survive} amp tertile(s) {'; '.join(amp_bits)}"))
    extra["amp_mae"] = amp_bits
    return _pack(state, rows, gates, "PASS", kind, extra, experiment, scale)


def _pack(state, rows, gates, decision, kind, extra, experiment="CHAN_BI_OF_STRATA_001", scale="15m bi-endpoint + 1m OF") -> dict:
    return {
        "experiment": experiment,
        "scale": scale,
        "decision": decision,
        "kind": kind,
        "n_15m": state.n_15m,
        "n_klc": state.n_klc,
        "n_events": len(rows),
        "gates": [asdict(g) for g in gates],
        "summary": extra,
        "events": rows,
        "blocked": "B1/B2=FORBIDDEN HTF=BLOCKED SMC=BLOCKED TF=BLOCKED classifier=FORBIDDEN not_edge",
    }
