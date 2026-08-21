"""C0 Join → C1 Identity → C2 Contrast → C3 Confound. No B1/B2. No combo score."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from chan_fractal_of.audit_b import _arr, _max_abs_cliff, _pct, cliffs_delta
from chan_fx_bi_trade_of.frozen_config import (
    BASELINE_N_BI,
    BASELINE_N_BOTTOM,
    BASELINE_N_ORDINARY,
    CLIFF_NEGLIGIBLE,
    DELTA_SIGN,
    FEATURE_DELTA,
    FEATURES_NEW,
    MIN_BIN_NEG,
    MIN_BIN_POS,
    MIN_GROUP,
    N_BINS,
    assert_clean,
)


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def join_ledgers(trade_rows: list[dict], fx_rows: list[dict]) -> tuple[list[dict], list[str], list[str], int]:
    fx = {r["fx_id"]: r for r in fx_rows}
    trade_ids = {r["fx_id"] for r in trade_rows}
    fx_ids = set(fx)
    missing = sorted(trade_ids - fx_ids)
    extra = sorted(fx_ids - trade_ids)
    side_mismatch = 0
    rows = []
    for t in trade_rows:
        f = fx.get(t["fx_id"])
        if f is None:
            continue
        if t.get("fx_side") != f.get("fx_side"):
            side_mismatch += 1
        rec = {
            "fx_id": t["fx_id"],
            "fx_side": t["fx_side"],
            "T_FX_VISIBLE": t["T_FX_VISIBLE"],
            "mid_range": float(t["mid_range"]),
            "kline_delta": float(t["kline_delta"]),
            "abs_delta": abs(float(t["kline_delta"])),
            "hhi": float(t["hhi"]),
            "push": float(t["push"]),
            "leak": int(t.get("leak") or 0),
            "retracted": bool(t.get("retracted", False)),
            "label_bi_endpoint": int(f["label_bi_endpoint"]),
        }
        assert_clean(rec)
        rows.append(rec)
    return rows, missing, extra, side_mismatch


def audit(rows: list[dict], missing: list[str], extra: list[str], side_mismatch: int, require_baseline_n: bool = True) -> dict:
    for r in rows:
        assert_clean(r)
    bottoms = [r for r in rows if r["fx_side"] == "BOTTOM"]
    bi = [r for r in bottoms if r["label_bi_endpoint"] == 1]
    ordinary = [r for r in bottoms if r["label_bi_endpoint"] == 0]
    gates: list[Gate] = []

    n_ok = len(bi) >= MIN_GROUP and len(ordinary) >= MIN_GROUP
    base_ok = (
        not require_baseline_n
        or (
            len(bottoms) == BASELINE_N_BOTTOM
            and len(ordinary) == BASELINE_N_ORDINARY
            and len(bi) == BASELINE_N_BI
        )
    )
    join_ok = not missing and not extra and side_mismatch == 0 and len(rows) > 0
    if not join_ok or not n_ok or not base_ok:
        gates.append(
            Gate(
                "C0",
                "FAIL",
                f"join missing={len(missing)} extra={len(extra)} side_mismatch={side_mismatch} "
                f"bottom={len(bottoms)} ordinary={len(ordinary)} bi={len(bi)}",
            )
        )
        for name in ("C1", "C2", "C3"):
            gates.append(Gate(name, "NOT_RUN", "C0 FAIL"))
        return _pack(rows, gates, "FAIL", "CLOCK", bottoms, bi, ordinary, {})
    gates.append(
        Gate(
            "C0",
            "PASS",
            f"join 1:1 n={len(rows)} bottom={len(bottoms)} ordinary={len(ordinary)} bi_endpoint={len(bi)}",
        )
    )

    leak = sum(int(r["leak"]) for r in rows)
    n_retract = sum(int(r["retracted"]) for r in rows)
    if leak or n_retract:
        gates.append(Gate("C1", "FAIL", f"leak={leak} retracted={n_retract}"))
        gates.extend([Gate("C2", "NOT_RUN", "C1 FAIL"), Gate("C3", "NOT_RUN", "C1 FAIL")])
        return _pack(rows, gates, "FAIL", "CLOCK", bottoms, bi, ordinary, {})
    gates.append(Gate("C1", "PASS", f"leak=0 retracted=0 n={len(rows)} label=sure-bi-only B1/B2=absent"))

    _, cliffs = _max_abs_cliff(bi, ordinary, (FEATURE_DELTA,) + FEATURES_NEW)
    cliff_d = cliffs[FEATURE_DELTA]
    delta_ok = np.isfinite(cliff_d) and np.sign(cliff_d) == DELTA_SIGN and abs(cliff_d) >= CLIFF_NEGLIGIBLE
    new_ok = [k for k in FEATURES_NEW if np.isfinite(cliffs[k]) and abs(cliffs[k]) >= CLIFF_NEGLIGIBLE]
    c2_detail = (
        f"cliff_delta={cliff_d:.3f} cliff_hhi={cliffs['hhi']:.3f} cliff_push={cliffs['push']:.3f} "
        f"bi_delta_p50={_pct(_arr(bi, FEATURE_DELTA, lambda _r: True))['p50']:.4g} "
        f"ord_delta_p50={_pct(_arr(ordinary, FEATURE_DELTA, lambda _r: True))['p50']:.4g}"
    )
    if not delta_ok:
        gates.append(Gate("C2", "FAIL", f"delta baseline not replicated {c2_detail}"))
        gates.append(Gate("C3", "NOT_RUN", "C2 FAIL"))
        return _pack(rows, gates, "FAIL", "CLOCK", bottoms, bi, ordinary, cliffs)
    if not new_ok:
        gates.append(Gate("C2", "FAIL", f"HHI and push no contrast {c2_detail}"))
        gates.append(Gate("C3", "NOT_RUN", "C2 FAIL"))
        extra = _summary(bottoms, bi, ordinary, cliffs)
        return _pack(rows, gates, "FAIL", "NO_INCREMENT", bottoms, bi, ordinary, cliffs, extra)
    gates.append(Gate("C2", "PASS", f"new={'+'.join(new_ok)} {c2_detail}"))

    amp_vals = np.array([r["mid_range"] for r in bottoms], dtype=float)
    dlt_vals = np.array([r["abs_delta"] for r in bottoms], dtype=float)
    amp_cliff = cliffs_delta(_arr(bi, "mid_range", lambda _r: True), _arr(ordinary, "mid_range", lambda _r: True))
    dlt_cliff = cliffs_delta(_arr(bi, "abs_delta", lambda _r: True), _arr(ordinary, "abs_delta", lambda _r: True))
    amp_max, amp_el, amp_rep = _bin_cliffs(bottoms, amp_vals, new_ok)
    dlt_max, dlt_el, dlt_rep = _bin_cliffs(bottoms, dlt_vals, new_ok)

    independent = []
    reasons = []
    for k in new_ok:
        a_ok, a_why = _confound_ok(amp_el, amp_max, k, amp_cliff)
        d_ok, d_why = _confound_ok(dlt_el, dlt_max, k, dlt_cliff)
        if a_ok and d_ok:
            independent.append(k)
            reasons.append(f"{k}:amp_{a_why}+delta_{d_why}")
        else:
            reasons.append(f"{k}:amp_{a_why}/delta_{d_why}")
    c3_detail = (
        f"independent={independent or 'none'} {' '.join(reasons)} "
        f"cliff_mid_range={amp_cliff:.3f} cliff_|delta|={dlt_cliff:.3f} "
        f"amp_bins={' | '.join(amp_rep)} delta_bins={' | '.join(dlt_rep)}"
    )
    if independent:
        gates.append(Gate("C3", "PASS", c3_detail))
        kind = "INDEPENDENT_STRUCTURE"
        decision = "PASS"
    else:
        gates.append(Gate("C3", "FAIL", c3_detail))
        kind = "NO_INCREMENT"
        decision = "FAIL"

    extra = _summary(bottoms, bi, ordinary, cliffs)
    extra["independent"] = independent
    extra["amp_cliff"] = amp_cliff
    extra["abs_delta_cliff"] = dlt_cliff
    extra["new_ok"] = new_ok
    return _pack(rows, gates, decision, kind, bottoms, bi, ordinary, cliffs, extra)


def _qcut(values: np.ndarray) -> np.ndarray:
    try:
        cats = pd.qcut(values, N_BINS, labels=False, duplicates="drop")
        return np.asarray(cats, dtype=int)
    except ValueError:
        return np.zeros(len(values), dtype=int)


def _bin_cliffs(bottoms: list[dict], bin_values: np.ndarray, keys: list[str]):
    cats = _qcut(bin_values)
    max_bin = int(cats.max()) if len(cats) else -1
    eligible = []
    report = []
    for b in sorted(set(int(c) for c in cats)):
        idx = [i for i, c in enumerate(cats) if int(c) == b]
        bucket = [bottoms[i] for i in idx]
        bpos = [r for r in bucket if r["label_bi_endpoint"] == 1]
        bneg = [r for r in bucket if r["label_bi_endpoint"] == 0]
        if len(bpos) < MIN_BIN_POS or len(bneg) < MIN_BIN_NEG:
            report.append(f"bin{b}:n_bi={len(bpos)} n_ord={len(bneg)} SKIP")
            continue
        _, bcliffs = _max_abs_cliff(bpos, bneg, tuple(keys))
        bits = " ".join(f"{k}={bcliffs[k]:.3f}" for k in keys)
        report.append(f"bin{b}:n_bi={len(bpos)} {bits}")
        eligible.append((b, bcliffs))
    return max_bin, eligible, report


def _survives_outside_max(eligible, max_bin, key) -> bool:
    return any(b != max_bin and abs(cliffs[key]) >= CLIFF_NEGLIGIBLE for b, cliffs in eligible)


def _survives_any(eligible, key) -> bool:
    return any(abs(cliffs[key]) >= CLIFF_NEGLIGIBLE for _, cliffs in eligible)


def _confound_ok(eligible, max_bin, key, confound_cliff) -> tuple[bool, str]:
    if not eligible:
        return False, "cannot_strip"
    strong = np.isfinite(confound_cliff) and abs(confound_cliff) >= CLIFF_NEGLIGIBLE
    if strong and not _survives_outside_max(eligible, max_bin, key):
        return False, "only_max_bin"
    if not _survives_any(eligible, key):
        return False, "within_bin_gone"
    return True, "ok"


def _topk_hits(rows: list[dict], key: str, k: int, higher_first: bool) -> int:
    vals = np.array([r[key] for r in rows], dtype=float)
    labs = np.array([r["label_bi_endpoint"] for r in rows], dtype=int)
    order = np.argsort(-vals if higher_first else vals)
    return int(labs[order][:k].sum())


def _summary(bottoms, bi, ordinary, cliffs) -> dict:
    k = len(bi)
    hhi_hi = float(np.median(_arr(bi, "hhi", lambda _r: True))) > float(np.median(_arr(ordinary, "hhi", lambda _r: True)))
    push_hi = float(np.median(_arr(bi, "push", lambda _r: True))) > float(np.median(_arr(ordinary, "push", lambda _r: True)))
    delta_hits = _topk_hits(bottoms, FEATURE_DELTA, k, higher_first=False)
    hhi_hits = _topk_hits(bottoms, "hhi", k, higher_first=hhi_hi)
    push_hits = _topk_hits(bottoms, "push", k, higher_first=push_hi)
    return {
        "n_bottom": len(bottoms),
        "n_bi": len(bi),
        "n_ordinary": len(ordinary),
        "base_rate": len(bi) / len(bottoms) if bottoms else float("nan"),
        "bi_delta": _pct(_arr(bi, FEATURE_DELTA, lambda _r: True)),
        "ord_delta": _pct(_arr(ordinary, FEATURE_DELTA, lambda _r: True)),
        "bi_hhi": _pct(_arr(bi, "hhi", lambda _r: True)),
        "ord_hhi": _pct(_arr(ordinary, "hhi", lambda _r: True)),
        "bi_push": _pct(_arr(bi, "push", lambda _r: True)),
        "ord_push": _pct(_arr(ordinary, "push", lambda _r: True)),
        "cliff_delta": cliffs.get(FEATURE_DELTA, float("nan")),
        "cliff_hhi": cliffs.get("hhi", float("nan")),
        "cliff_push": cliffs.get("push", float("nan")),
        "auc_delta_lower": (1.0 - cliffs.get(FEATURE_DELTA, float("nan"))) / 2.0,
        "auc_hhi_higher": (1.0 + cliffs.get("hhi", float("nan"))) / 2.0,
        "topk_delta": {"k": k, "hits": delta_hits, "rate": delta_hits / k if k else float("nan")},
        "topk_hhi": {"k": k, "hits": hhi_hits, "higher_first": hhi_hi, "rate": hhi_hits / k if k else float("nan")},
        "topk_push": {"k": k, "hits": push_hits, "higher_first": push_hi, "rate": push_hits / k if k else float("nan")},
    }


def _pack(rows, gates, decision, kind, bottoms, bi, ordinary, cliffs, extra=None) -> dict:
    return {
        "experiment": "CHAN_FX_BI_TRADE_OF_001",
        "phase": "contrast",
        "scale": "15m Fractal + aggTrades HHI/push",
        "decision": decision,
        "kind": kind,
        "n_events": len(rows),
        "n_bottom": len(bottoms),
        "n_bi": len(bi),
        "n_ordinary": len(ordinary),
        "gates": [asdict(g) for g in gates],
        "summary": extra or {},
        "blocked": "≠NEW_EDGE 不准 B1/B2 HTF SMC 5m absorption classifier 交易层 Phase3-HHI",
    }
