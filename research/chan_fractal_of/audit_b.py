"""B0 → B1 Contrast → B2 Confound → B3 Bi-only. Earlier FAIL stops later gates."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from chan_fractal_of.clock import ClockState, FractalEvent
from chan_fractal_of.frozen_config import (
    CLIFF_NEGLIGIBLE,
    MIN_BIN_NEG,
    MIN_BIN_POS,
    MIN_POS_B1_B2,
    N_AMP_BINS,
    PHASE_B_FEATURES,
    assert_phase_b_features_clean,
)
from chan_fractal_of.labels import TruthIndex, attach_labels
from chan_fractal_of.of_window import snapshots_for_event


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def cliffs_delta(pos: np.ndarray, neg: np.ndarray) -> float:
    a = np.asarray(pos, dtype=float)
    b = np.asarray(neg, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    gt = np.sum(a[:, None] > b[None, :])
    lt = np.sum(a[:, None] < b[None, :])
    return float((gt - lt) / (len(a) * len(b)))


def _pct(x: np.ndarray) -> dict[str, float]:
    if len(x) == 0:
        return {"n": 0, "p10": float("nan"), "p50": float("nan"), "p90": float("nan")}
    return {
        "n": int(len(x)),
        "p10": float(np.percentile(x, 10)),
        "p50": float(np.percentile(x, 50)),
        "p90": float(np.percentile(x, 90)),
    }


def _arr(rows: list[dict], key: str, pred) -> np.ndarray:
    return np.array([r[key] for r in rows if pred(r)], dtype=float)


def _feature_record(ev: FractalEvent, of: pd.DataFrame) -> dict:
    snaps = snapshots_for_event(ev, of)
    rec = {
        "fx_id": ev.fx_id,
        "fx_side": ev.fx_side,
        "T_FX_VISIBLE": str(ev.T_FX_VISIBLE),
        "mid_range": ev.mid_range,
        "of_taker_buy_forming": snaps["forming"].of_taker_buy,
        "of_taker_sell_forming": snaps["forming"].of_taker_sell,
        "of_delta_forming": snaps["forming"].of_delta,
        "of_imbalance_forming": snaps["forming"].of_imbalance,
        "of_volume_forming": snaps["forming"].of_volume,
        "of_n_forming": snaps["forming"].n_1m,
        "leak": snaps["forming"].future_leak,
    }
    assert_phase_b_features_clean(rec)
    return rec


def _max_abs_cliff(pos: list[dict], neg: list[dict], keys: tuple[str, ...]) -> tuple[float, dict[str, float]]:
    out: dict[str, float] = {}
    best = 0.0
    for k in keys:
        d = cliffs_delta(_arr(pos, k, lambda _r: True), _arr(neg, k, lambda _r: True))
        out[k] = d
        if np.isfinite(d):
            best = max(best, abs(d))
    return best, out


def audit_b(state: ClockState, of: pd.DataFrame, truth: TruthIndex) -> dict:
    rows = []
    leak_total = 0
    of_keys = set(PHASE_B_FEATURES)
    for ev in state.events:
        rec = _feature_record(ev, of)
        leak_total += rec["leak"]
        rec.update(attach_labels(ev.fx_id, ev.fx_side, truth))
        extra = set(rec) & {"B1", "B2", "strength_score"}
        if extra:
            raise ValueError(f"label leaked into feature namespace: {extra}")
        if of_keys.intersection(rec) and rec["leak"]:
            pass
        rows.append(rec)

    bottoms = [r for r in rows if r["fx_side"] == "BOTTOM"]
    pos = [r for r in bottoms if r["label_B1_B2"] == 1]
    neg = [r for r in bottoms if r["label_B1_B2"] == 0]
    of_contrast_keys = ("of_delta_forming", "of_imbalance_forming")

    gates: list[Gate] = []

    # B0
    if leak_total != 0:
        gates.append(Gate("B0", "FAIL", f"future OF leak={leak_total}"))
    else:
        gates.append(
            Gate(
                "B0",
                "PASS",
                f"leak=0 n_fx={len(rows)} bottom={len(bottoms)} "
                f"bi_ep={sum(r['label_bi_endpoint'] for r in bottoms)} "
                f"B1={sum(r['label_B1'] for r in bottoms)} B1_B2={len(pos)} "
                f"engine_b1={truth.n_b1} engine_b2={truth.n_b2}",
            )
        )
    if gates[-1].verdict != "PASS":
        gates.extend(
            [
                Gate("B1", "NOT_RUN", "B0 FAIL"),
                Gate("B2", "NOT_RUN", "B0 FAIL"),
                Gate("B3", "NOT_RUN", "B0 FAIL"),
            ]
        )
        return _pack(state, rows, gates, "FAIL", truth)

    # B1 Contrast
    if len(pos) < MIN_POS_B1_B2:
        gates.append(Gate("B1", "FAIL", f"n_B1_B2={len(pos)} < {MIN_POS_B1_B2}"))
    else:
        best, cliffs = _max_abs_cliff(pos, neg, of_contrast_keys)
        detail = (
            f"n_pos={len(pos)} n_neg={len(neg)} "
            f"cliff_delta={cliffs['of_delta_forming']:.3f} "
            f"cliff_imb={cliffs['of_imbalance_forming']:.3f} "
            f"pos_delta_p50={_pct(_arr(pos, 'of_delta_forming', lambda _r: True))['p50']:.4g} "
            f"neg_delta_p50={_pct(_arr(neg, 'of_delta_forming', lambda _r: True))['p50']:.4g}"
        )
        if best < CLIFF_NEGLIGIBLE:
            gates.append(Gate("B1", "FAIL", f"no OF contrast |δ|={best:.3f}<{CLIFF_NEGLIGIBLE} {detail}"))
        else:
            gates.append(Gate("B1", "PASS", detail))

    if gates[-1].verdict != "PASS":
        gates.extend([Gate("B2", "NOT_RUN", "B1 FAIL"), Gate("B3", "NOT_RUN", "B1 FAIL")])
        extra = _summaries(bottoms, pos, neg, {})
        return _pack(state, rows, gates, "FAIL", truth, extra)

    # B2 Confound: difference must survive amplitude matching, not only the largest-range bin.
    amp_best, amp_cliffs = _max_abs_cliff(pos, neg, ("mid_range",))
    bin_report = []
    eligible = []
    max_bin = -1
    if len(bottoms) >= N_AMP_BINS:
        ranges = np.array([r["mid_range"] for r in bottoms], dtype=float)
        try:
            cats = pd.qcut(ranges, N_AMP_BINS, labels=False, duplicates="drop")
        except ValueError:
            cats = np.zeros(len(bottoms), dtype=int)
        max_bin = int(max(cats))
        for b in sorted(set(int(c) for c in cats)):
            idx = [i for i, c in enumerate(cats) if int(c) == b]
            bucket = [bottoms[i] for i in idx]
            bpos = [r for r in bucket if r["label_B1_B2"] == 1]
            bneg = [r for r in bucket if r["label_B1_B2"] == 0]
            if len(bpos) < MIN_BIN_POS or len(bneg) < MIN_BIN_NEG:
                bin_report.append(f"bin{b}:n_pos={len(bpos)} n_neg={len(bneg)} SKIP")
                continue
            best, cliffs = _max_abs_cliff(bpos, bneg, of_contrast_keys)
            bin_report.append(
                f"bin{b}:n_pos={len(bpos)} cliff_delta={cliffs['of_delta_forming']:.3f} cliff_imb={cliffs['of_imbalance_forming']:.3f}"
            )
            eligible.append((b, best))
    else:
        bin_report.append("too few bottoms to bin")

    of_in_non_top = any(b != max_bin and best >= CLIFF_NEGLIGIBLE for b, best in eligible)
    of_in_any = any(best >= CLIFF_NEGLIGIBLE for _, best in eligible)
    amp_strong = np.isfinite(amp_cliffs["mid_range"]) and abs(amp_cliffs["mid_range"]) >= CLIFF_NEGLIGIBLE
    amp_detail = f"cliff_mid_range={amp_cliffs['mid_range']:.3f} bins={' | '.join(bin_report)}"
    if not eligible:
        gates.append(Gate("B2", "FAIL", f"cannot strip amplitude; no matched bin {amp_detail}"))
    elif amp_strong and not of_in_non_top:
        gates.append(
            Gate(
                "B2",
                "FAIL",
                f"amplitude effect; OF only testable in largest-range bin {amp_detail}",
            )
        )
    elif not of_in_any:
        gates.append(Gate("B2", "FAIL", f"within-bin OF gone {amp_detail}"))
    else:
        gates.append(Gate("B2", "PASS", f"within-bin OF remains outside amplitude pile-up {amp_detail}"))

    if gates[-1].verdict != "PASS":
        gates.append(Gate("B3", "NOT_RUN", "B2 FAIL"))
        extra = _summaries(bottoms, pos, neg, {"amp_cliff": amp_cliffs["mid_range"]})
        return _pack(state, rows, gates, "FAIL", truth, extra)

    # B3 Bi-only: among bi endpoints, does B1_B2 still differ?
    bi_rows = [r for r in bottoms if r["label_bi_endpoint"] == 1]
    bi_pos = [r for r in bi_rows if r["label_B1_B2"] == 1]
    bi_neg = [r for r in bi_rows if r["label_B1_B2"] == 0]
    non_bi = [r for r in bottoms if r["label_bi_endpoint"] == 0]
    bi_vs_not_best, bi_vs_not = _max_abs_cliff(bi_rows, non_bi, of_contrast_keys)
    if len(bi_pos) < MIN_POS_B1_B2 or len(bi_neg) < MIN_BIN_NEG:
        gates.append(
            Gate(
                "B3",
                "FAIL",
                f"cannot separate B1_B2 from bi-only n_bi_pos={len(bi_pos)} n_bi_neg={len(bi_neg)} "
                f"cliff_bi_vs_not_delta={bi_vs_not['of_delta_forming']:.3f}",
            )
        )
    else:
        best, cliffs = _max_abs_cliff(bi_pos, bi_neg, of_contrast_keys)
        detail = (
            f"among_bi n_pos={len(bi_pos)} n_neg={len(bi_neg)} "
            f"cliff_delta={cliffs['of_delta_forming']:.3f} cliff_imb={cliffs['of_imbalance_forming']:.3f} "
            f"bi_vs_not_delta={bi_vs_not['of_delta_forming']:.3f} bi_vs_not_imb={bi_vs_not['of_imbalance_forming']:.3f}"
        )
        if best < CLIFF_NEGLIGIBLE:
            gates.append(Gate("B3", "FAIL", f"OF contrast is bi-only |δ|={best:.3f} {detail}"))
        else:
            gates.append(Gate("B3", "PASS", detail))

    decision = "PASS" if gates[-1].verdict == "PASS" else "FAIL"
    extra = _summaries(
        bottoms,
        pos,
        neg,
        {
            "amp_cliff": amp_cliffs["mid_range"],
            "bi_vs_not_delta": bi_vs_not["of_delta_forming"],
            "bi_vs_not_imb": bi_vs_not["of_imbalance_forming"],
        },
    )
    return _pack(state, rows, gates, decision, truth, extra)


def _summaries(bottoms, pos, neg, extra: dict) -> dict:
    out = {
        "n_bottom": len(bottoms),
        "n_pos": len(pos),
        "n_neg": len(neg),
        "n_bi_endpoint": sum(r["label_bi_endpoint"] for r in bottoms),
        "n_B1": sum(r["label_B1"] for r in bottoms),
        "pos_delta": _pct(_arr(pos, "of_delta_forming", lambda _r: True)),
        "neg_delta": _pct(_arr(neg, "of_delta_forming", lambda _r: True)),
        "pos_imb": _pct(_arr(pos, "of_imbalance_forming", lambda _r: True)),
        "neg_imb": _pct(_arr(neg, "of_imbalance_forming", lambda _r: True)),
        "pos_range": _pct(_arr(pos, "mid_range", lambda _r: True)),
        "neg_range": _pct(_arr(neg, "mid_range", lambda _r: True)),
        "cliff_delta": cliffs_delta(
            _arr(pos, "of_delta_forming", lambda _r: True),
            _arr(neg, "of_delta_forming", lambda _r: True),
        )
        if pos and neg
        else float("nan"),
        "cliff_imb": cliffs_delta(
            _arr(pos, "of_imbalance_forming", lambda _r: True),
            _arr(neg, "of_imbalance_forming", lambda _r: True),
        )
        if pos and neg
        else float("nan"),
        "cliff_mid_range": cliffs_delta(
            _arr(pos, "mid_range", lambda _r: True),
            _arr(neg, "mid_range", lambda _r: True),
        )
        if pos and neg
        else float("nan"),
    }
    out.update(extra)
    return out


def _pack(state, rows, gates, decision, truth: TruthIndex, extra=None) -> dict:
    return {
        "experiment": "CHAN_FRACTAL_OF_001",
        "phase": "B",
        "scale": "15m Fractal + 1m OF",
        "decision": decision,
        "n_15m": state.n_15m,
        "n_klc": state.n_klc,
        "n_events": len(rows),
        "truth": {
            "n_sure_bi": truth.n_sure_bi,
            "n_zs_sure": truth.n_zs_sure,
            "n_b1": truth.n_b1,
            "n_b2": truth.n_b2,
            "n_b1_b2_fx": len(truth.b1_b2_fx),
            "n_s1": truth.n_s1,
            "n_s2": truth.n_s2,
        },
        "gates": [asdict(g) for g in gates],
        "summary": extra or {},
        "events": rows,
        "blocked": "HTF=BLOCKED SMC=BLOCKED classifier=FORBIDDEN TF_compare=FORBIDDEN",
    }
