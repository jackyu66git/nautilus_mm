"""CHAN_3RD_POINT_END_001. Pre-T3 HTF context of REENTRY vs RESUME. No EMA."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_3rd_point_end.context import box_dist, htf_at, stream_htf
from chan_3rd_point_end.paths import EXPECTED_N_15M, EXPECTED_N_3, FATE, KLINE_1M, LOG, MOTHER
from chan_fractal_of.clock import resample_bars


def _p50(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2]


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    mother = [json.loads(l) for l in MOTHER.read_text().splitlines() if l]
    fate = {json.loads(l)["event_id"]: json.loads(l) for l in FATE.read_text().splitlines() if l}
    k1 = pd.read_parquet(KLINE_1M)
    bar_15 = resample_bars(k1, 15)
    bar_1h = resample_bars(k1, 60)
    snaps = stream_htf(bar_1h)
    ordered = sorted(mother, key=lambda e: e["T_3_VISIBLE"])
    prior_same = {"B3": 0, "S3": 0}
    rows = []
    for ev in ordered:
        fid = ev["event_id"]
        ft = fate[fid]
        t3 = pd.Timestamp(ev["T_3_VISIBLE"])
        ctx = htf_at(snaps, t3)
        i0 = int(ev["tape_row"])
        px = float(bar_15.iloc[i0]["close"])
        rec = {
            "event_id": fid,
            "kind": ev["kind"],
            "fate": ft["fate"],
            "T_3_VISIBLE": ev["T_3_VISIBLE"],
            "htf_state": None if ctx is None else ctx["state"],
            "trend_age_h": None if ctx is None else ctx["age_h"],
            "segment": None if ctx is None else ctx["segment"],
            "run_atr": None if ctx is None else ctx["run_atr"],
            "box_dist_atr": None
            if ctx is None
            else box_dist(ev["kind"], px, ctx["zg"], ctx["zd"], ctx["atr"]),
            "n_prior_3rd_same": prior_same[ev["kind"]],
        }
        rows.append(rec)
        prior_same[ev["kind"]] += 1

    re_n = [r for r in rows if r["fate"] == "REENTRY"]
    rs_n = [r for r in rows if r["fate"] == "RESUME"]
    clock_ok = all(r["htf_state"] is not None for r in rows) and len(rows) == EXPECTED_N_3
    if len(bar_15) != EXPECTED_N_15M or not clock_ok:
        decision, kind = "FAIL", "CLOCK"
    else:
        decision, kind = "PASS", "ATTRIBUTION_OK"
    lateish = {"LATE", "SHIFT"}
    n_re_late = sum(1 for r in re_n if r["segment"] in lateish)
    n_rs_late = sum(1 for r in rs_n if r["segment"] in lateish)
    candidate = (
        len(re_n) == 2
        and n_re_late == 2
        and (n_rs_late / len(rs_n) if rs_n else 1) < 0.5
    )
    result = {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "n_3": len(rows),
        "n_resume": len(rs_n),
        "n_reentry": len(re_n),
        "reentry_segments": [r["segment"] for r in re_n],
        "reentry_states": [r["htf_state"] for r in re_n],
        "reentry_age_h": [r["trend_age_h"] for r in re_n],
        "reentry_box_dist": [r["box_dist_atr"] for r in re_n],
        "reentry_prior_3rd": [r["n_prior_3rd_same"] for r in re_n],
        "resume_segment_n": dict(Counter(r["segment"] for r in rs_n)),
        "resume_state_n": dict(Counter(r["htf_state"] for r in rs_n)),
        "resume_age_h_p50": _p50([r["trend_age_h"] for r in rs_n if r["trend_age_h"] is not None]),
        "reentry_age_h_p50": _p50([r["trend_age_h"] for r in re_n if r["trend_age_h"] is not None]),
        "resume_box_p50": _p50([r["box_dist_atr"] for r in rs_n if r["box_dist_atr"] is not None]),
        "reentry_box_p50": _p50([r["box_dist_atr"] for r in re_n if r["box_dist_atr"] is not None]),
        "n_resume_late_or_shift": n_rs_late,
        "n_reentry_late_or_shift": n_re_late,
        "candidate_late_split": candidate,
        "not_proof": True,
        "blocked": "n_REENTRY=2。不准改三买定义。不准当 Fate Contrast。无 EMA/OF。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in rows) + "\n"
    )
    lines = [
        f"CHAN_3RD_POINT_END_001  decision={decision}  kind={kind}",
        "T_3 前 1H 结构。问 REENTRY 是否已在不同前置状态。不准改三买。",
        "",
        f"  n_3={len(rows)} RESUME={len(rs_n)} REENTRY={len(re_n)}",
        f"  REENTRY segment={result['reentry_segments']} state={result['reentry_states']}",
        f"  REENTRY age_h={result['reentry_age_h']} box_dist={result['reentry_box_dist']}",
        f"  REENTRY n_prior_3rd_same={result['reentry_prior_3rd']}",
        f"  RESUME  segment={result['resume_segment_n']} state={result['resume_state_n']}",
        f"  age_h p50  RESUME={result['resume_age_h_p50']} REENTRY={result['reentry_age_h_p50']}",
        f"  box p50    RESUME={result['resume_box_p50']} REENTRY={result['reentry_box_p50']}",
        f"  LATE|SHIFT RESUME={n_rs_late}/18 REENTRY={n_re_late}/2",
        f"  candidate_late_split={candidate}  not_proof=True",
        "",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
