"""C0 Size → C1 Identity → C2 Contrast → C3 Confound. No B1/B2."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from chan_fractal_of.audit_b import _arr, _max_abs_cliff, _pct, cliffs_delta
from chan_fractal_of.clock import ClockState
from chan_fractal_of.of_window import snapshots_for_event
from chan_fx_bi_of.frozen_config import (
    CLIFF_NEGLIGIBLE,
    CONFOUND,
    MIN_BIN_NEG,
    MIN_BIN_POS,
    MIN_GROUP,
    N_AMP_BINS,
    assert_clean,
)
from chan_fx_bi_of.truth import BiOnlyIndex


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def _feature_record(ev, of: pd.DataFrame) -> dict:
    snaps = snapshots_for_event(ev, of)
    rec = {
        "fx_id": ev.fx_id,
        "fx_side": ev.fx_side,
        "T_FX_VISIBLE": str(ev.T_FX_VISIBLE),
        "retracted": ev.retracted,
        "mid_range": ev.mid_range,
        "of_taker_buy_forming": snaps["forming"].of_taker_buy,
        "of_taker_sell_forming": snaps["forming"].of_taker_sell,
        "of_delta_forming": snaps["forming"].of_delta,
        "of_imbalance_forming": snaps["forming"].of_imbalance,
        "of_volume_forming": snaps["forming"].of_volume,
        "of_n_forming": snaps["forming"].n_1m,
        "leak": snaps["forming"].future_leak,
    }
    assert_clean(rec)
    return rec


def audit(state: ClockState, of: pd.DataFrame, truth: BiOnlyIndex) -> dict:
    rows = []
    leak_total = 0
    n_retract = 0
    for ev in state.events:
        rec = _feature_record(ev, of)
        leak_total += rec["leak"]
        n_retract += int(rec["retracted"])
        rec["label_bi_endpoint"] = int(ev.fx_id in truth.endpoints)
        assert_clean(rec)
        rows.append(rec)

    bottoms = [r for r in rows if r["fx_side"] == "BOTTOM"]
    bi = [r for r in bottoms if r["label_bi_endpoint"] == 1]
    ordinary = [r for r in bottoms if r["label_bi_endpoint"] == 0]
    of_keys = ("of_delta_forming", "of_imbalance_forming")
    gates: list[Gate] = []

    # C0
    if len(bi) < MIN_GROUP or len(ordinary) < MIN_GROUP:
        gates.append(Gate("C0", "FAIL", f"n_bi={len(bi)} n_ordinary={len(ordinary)} min={MIN_GROUP}"))
    else:
        gates.append(
            Gate(
                "C0",
                "PASS",
                f"bottom={len(bottoms)} ordinary={len(ordinary)} bi_endpoint={len(bi)} "
                f"sure_bi={truth.n_sure_bi} unmatched_ep={len(truth.endpoints - {r['fx_id'] for r in rows})}",
            )
        )
    if gates[-1].verdict != "PASS":
        gates.extend(
            [
                Gate("C1", "NOT_RUN", "C0 FAIL"),
                Gate("C2", "NOT_RUN", "C0 FAIL"),
                Gate("C3", "NOT_RUN", "C0 FAIL"),
            ]
        )
        return _pack(state, rows, gates, "FAIL", truth)

    # C1
    n_form_empty = sum(1 for r in rows if r["of_n_forming"] == 0)
    if leak_total != 0:
        gates.append(Gate("C1", "FAIL", f"future OF leak={leak_total}"))
    elif n_retract != 0:
        gates.append(Gate("C1", "FAIL", f"fx retracted={n_retract}"))
    else:
        gates.append(
            Gate(
                "C1",
                "PASS",
                f"leak=0 retracted=0 forming_empty={n_form_empty}/{len(rows)} "
                f"unsure_bi={truth.n_unsure_bi} label=sure-bi-only B1/B2=absent",
            )
        )
    if gates[-1].verdict != "PASS":
        gates.extend([Gate("C2", "NOT_RUN", "C1 FAIL"), Gate("C3", "NOT_RUN", "C1 FAIL")])
        return _pack(state, rows, gates, "FAIL", truth)

    # C2
    best, cliffs = _max_abs_cliff(bi, ordinary, of_keys)
    detail = (
        f"cliff_delta={cliffs['of_delta_forming']:.3f} cliff_imb={cliffs['of_imbalance_forming']:.3f} "
        f"bi_delta_p50={_pct(_arr(bi, 'of_delta_forming', lambda _r: True))['p50']:.4g} "
        f"ord_delta_p50={_pct(_arr(ordinary, 'of_delta_forming', lambda _r: True))['p50']:.4g}"
    )
    if best < CLIFF_NEGLIGIBLE:
        gates.append(Gate("C2", "FAIL", f"ordinary ≈ bi-endpoint |δ|={best:.3f} {detail}"))
    else:
        gates.append(Gate("C2", "PASS", detail))
    if gates[-1].verdict != "PASS":
        gates.append(Gate("C3", "NOT_RUN", "C2 FAIL"))
        extra = _summary(bottoms, bi, ordinary, cliffs)
        return _pack(state, rows, gates, "FAIL", truth, extra)

    # C3 amplitude
    amp_best, amp_cliffs = _max_abs_cliff(bi, ordinary, CONFOUND)
    bin_report = []
    eligible = []
    max_bin = -1
    ranges = np.array([r["mid_range"] for r in bottoms], dtype=float)
    try:
        cats = pd.qcut(ranges, N_AMP_BINS, labels=False, duplicates="drop")
    except ValueError:
        cats = np.zeros(len(bottoms), dtype=int)
    max_bin = int(max(cats))
    for b in sorted(set(int(c) for c in cats)):
        idx = [i for i, c in enumerate(cats) if int(c) == b]
        bucket = [bottoms[i] for i in idx]
        bpos = [r for r in bucket if r["label_bi_endpoint"] == 1]
        bneg = [r for r in bucket if r["label_bi_endpoint"] == 0]
        if len(bpos) < MIN_BIN_POS or len(bneg) < MIN_BIN_NEG:
            bin_report.append(f"bin{b}:n_bi={len(bpos)} n_ord={len(bneg)} SKIP")
            continue
        bbest, bcliffs = _max_abs_cliff(bpos, bneg, of_keys)
        bin_report.append(
            f"bin{b}:n_bi={len(bpos)} cliff_delta={bcliffs['of_delta_forming']:.3f} cliff_imb={bcliffs['of_imbalance_forming']:.3f}"
        )
        eligible.append((b, bbest))
    of_in_non_top = any(b != max_bin and best >= CLIFF_NEGLIGIBLE for b, best in eligible)
    of_in_any = any(best >= CLIFF_NEGLIGIBLE for _, best in eligible)
    amp_strong = np.isfinite(amp_cliffs["mid_range"]) and abs(amp_cliffs["mid_range"]) >= CLIFF_NEGLIGIBLE
    amp_detail = f"cliff_mid_range={amp_cliffs['mid_range']:.3f} bins={' | '.join(bin_report)}"
    if not eligible:
        gates.append(Gate("C3", "FAIL", f"cannot strip amplitude {amp_detail}"))
    elif amp_strong and not of_in_non_top:
        gates.append(Gate("C3", "FAIL", f"amplitude effect; OF only testable in largest-range bin {amp_detail}"))
    elif not of_in_any:
        gates.append(Gate("C3", "FAIL", f"within-bin OF gone {amp_detail}"))
    else:
        gates.append(Gate("C3", "PASS", f"within-bin OF remains outside amplitude pile-up {amp_detail}"))

    decision = "PASS" if gates[-1].verdict == "PASS" else "FAIL"
    extra = _summary(bottoms, bi, ordinary, cliffs)
    extra["amp_cliff"] = amp_cliffs["mid_range"]
    return _pack(state, rows, gates, decision, truth, extra)


def _summary(bottoms, bi, ordinary, cliffs) -> dict:
    return {
        "n_bottom": len(bottoms),
        "n_bi": len(bi),
        "n_ordinary": len(ordinary),
        "bi_delta": _pct(_arr(bi, "of_delta_forming", lambda _r: True)),
        "ord_delta": _pct(_arr(ordinary, "of_delta_forming", lambda _r: True)),
        "bi_imb": _pct(_arr(bi, "of_imbalance_forming", lambda _r: True)),
        "ord_imb": _pct(_arr(ordinary, "of_imbalance_forming", lambda _r: True)),
        "bi_range": _pct(_arr(bi, "mid_range", lambda _r: True)),
        "ord_range": _pct(_arr(ordinary, "mid_range", lambda _r: True)),
        "cliff_delta": cliffs.get("of_delta_forming", float("nan")),
        "cliff_imb": cliffs.get("of_imbalance_forming", float("nan")),
        "cliff_mid_range": cliffs_delta(
            _arr(bi, "mid_range", lambda _r: True),
            _arr(ordinary, "mid_range", lambda _r: True),
        )
        if bi and ordinary
        else float("nan"),
    }


def _pack(state, rows, gates, decision, truth: BiOnlyIndex, extra=None) -> dict:
    return {
        "experiment": "CHAN_FX_BI_OF_001",
        "phase": "contrast",
        "scale": "15m Fractal + 1m OF",
        "decision": decision,
        "n_15m": state.n_15m,
        "n_klc": state.n_klc,
        "n_events": len(rows),
        "truth": {
            "n_sure_bi": truth.n_sure_bi,
            "n_unsure_bi": truth.n_unsure_bi,
            "n_endpoints": len(truth.endpoints),
        },
        "gates": [asdict(g) for g in gates],
        "summary": extra or {},
        "events": rows,
        "blocked": "B1/B2=FORBIDDEN HTF=BLOCKED SMC=BLOCKED TF_compare=FORBIDDEN",
    }
