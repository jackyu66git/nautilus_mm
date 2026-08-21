"""CHAN_2ND_POINT_FATE_001. 15m 2nd-point fate. 3rd-point HOLD. No EMA."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_2nd_point_fate.paths import EXPECTED_N_15M, KLINE_1M, LOG
from chan_2nd_point_fate.scan import follow_fate, scan_second
from chan_fractal_of.clock import resample_bars


def _p50(xs):
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2]


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    payload = scan_second(bar)
    rows = [follow_fate(ev, bar) for ev in payload["events"]]
    clock_ok = all(r["T_2_VISIBLE"] < r["T_FATE"] for r in rows) if rows else True
    n = len(rows)
    fate_n = Counter(r["fate"] for r in rows)
    n_in = sum(1 for r in rows if r["in_box_at_t2"])
    if len(bar) != EXPECTED_N_15M:
        decision, kind = "FAIL", "CLOCK"
    elif not clock_ok:
        decision, kind = "FAIL", "LEAK"
    elif n == 0:
        decision, kind = "FAIL", "NO_OBJECT"
    else:
        decision, kind = "PASS", "FATE_CENSUS_OK"
    result = {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "n_15m": payload["n_15m"],
        "n_leave": payload["n_leave"],
        "n_no_first": payload["n_no_first"],
        "n_broke_first": payload["n_broke_first"],
        "n_b2": payload["n_b2"],
        "n_s2": payload["n_s2"],
        "n_2": n,
        "n_in_box_at_t2": n_in,
        "n_resume": fate_n["RESUME"],
        "n_reentry": fate_n["REENTRY"],
        "n_reverse": fate_n["REVERSE"],
        "n_censor": fate_n["CENSOR"],
        "resume_rate": round(fate_n["RESUME"] / n, 6) if n else None,
        "hours_to_fate_p50": _p50([r["hours_to_fate"] for r in rows]),
        "blocked": "三买 HOLD。无 EMA/OF/Trend Age。不准放宽一类门槛。不准扩窗。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in rows) + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_2ND_POINT_FATE_001  decision={decision}  kind={kind}",
        "15m 二买/二卖 Fate。三买线不动。无 EMA。",
        "",
        f"  n_leave={payload['n_leave']} no_first={payload['n_no_first']} broke_first={payload['n_broke_first']}",
        f"  n_b2={payload['n_b2']} n_s2={payload['n_s2']} n_2={n} in_box_at_t2={n_in}",
        f"  fate RESUME={fate_n['RESUME']} REENTRY={fate_n['REENTRY']} "
        f"REVERSE={fate_n['REVERSE']} CENSOR={fate_n['CENSOR']}",
        f"  resume_rate={result['resume_rate']} hours_p50={result['hours_to_fate_p50']}",
        "",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
