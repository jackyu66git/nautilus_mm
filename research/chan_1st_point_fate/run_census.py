"""CHAN_1ST_POINT_FATE_001. Engine B1/S1 fate. B2/B3 HOLD. No EMA."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_1st_point_fate.paths import EXPECTED_N_15M, KLINE_1M, LOG
from chan_1st_point_fate.scan import follow_fate, scan_first
from chan_fractal_of.clock import resample_bars


def _p50(xs):
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2]


def _hist(hours: list[float]) -> str:
    from collections import Counter

    c = Counter(hours)
    return ", ".join(f"{h}h×{n}" for h, n in sorted(c.items()))


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    payload = scan_first(bar)
    rows = [follow_fate(ev, bar) for ev in payload["events"]]
    clock_ok = all(str(r["T_1_VISIBLE"]) < str(r["T_FATE"]) for r in rows) if rows else True
    n = len(rows)
    fate_n = Counter(r["fate"] for r in rows)
    hours = [r["hours_to_fate"] for r in rows]
    n_next = sum(1 for h in hours if h == 0.25)
    n_in = sum(1 for r in rows if r["in_box_at_t1"])
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
        "n_b1": payload["n_b1"],
        "n_s1": payload["n_s1"],
        "n_1": n,
        "n_in_box_at_t1": n_in,
        "n_resume": fate_n["RESUME"],
        "n_reentry": fate_n["REENTRY"],
        "n_reverse": fate_n["REVERSE"],
        "n_censor": fate_n["CENSOR"],
        "n_next_bar_fate": n_next,
        "resume_rate": round(fate_n["RESUME"] / n, 6) if n else None,
        "hours_to_fate_p50": _p50(hours),
        "hours_to_fate_means": "confirmation→fate bar latency. ≠ duration.",
        "blocked": "B2/B3 HOLD。无 EMA/OF/Trend Age。不准改一类。不准用 find_first_bsp。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in rows) + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_1ST_POINT_FATE_001  decision={decision}  kind={kind}",
        "引擎 B1/S1 Fate。B2/B3 不动。无 EMA。",
        "",
        f"  n_b1={payload['n_b1']} n_s1={payload['n_s1']} n_1={n} in_box_at_t1={n_in}",
        f"  fate RESUME={fate_n['RESUME']} REENTRY={fate_n['REENTRY']} "
        f"REVERSE={fate_n['REVERSE']} CENSOR={fate_n['CENSOR']}",
        f"  resume_rate={result['resume_rate']} hours_to_fate_p50={result['hours_to_fate_p50']}",
        f"  next_bar_fate={n_next}/{n}  （判定延迟，≠持仓）",
        f"  latency_hist: {_hist(hours) if hours else 'none'}",
        "",
        "hours_to_fate = confirmation → fate bar latency。1根15m=0.25h。",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
