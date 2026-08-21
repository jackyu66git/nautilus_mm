"""CHAN_3RD_POINT_FATE_001. 15m 3rd-point fate after T_3. No EMA."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_3rd_point_fate.paths import (
    EXPECTED_N_15M,
    EXPECTED_N_3,
    KLINE_1M,
    LOG,
    MOTHER,
    N_LEAVE,
    N_PULLBACK_IN,
)
from chan_3rd_point_fate.scan import follow_fate
from chan_fractal_of.clock import resample_bars


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    events = [json.loads(l) for l in MOTHER.read_text().splitlines() if l]
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    rows = [follow_fate(ev, bar) for ev in events]
    clock_ok = all(r["T_3_VISIBLE"] < r["T_FATE"] for r in rows)
    fate_n = Counter(r["fate"] for r in rows)
    n = len(rows)
    if len(bar) != EXPECTED_N_15M or n != EXPECTED_N_3 or not clock_ok:
        decision, kind = "FAIL", "CLOCK"
    else:
        decision, kind = "PASS", "FATE_CENSUS_OK"
    hours = sorted(r["hours_to_fate"] for r in rows)
    result = {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "n_leave": N_LEAVE,
        "n_pullback_in": N_PULLBACK_IN,
        "n_3": n,
        "n_b3": sum(1 for r in rows if r["kind"] == "B3"),
        "n_s3": sum(1 for r in rows if r["kind"] == "S3"),
        "n_resume": fate_n["RESUME"],
        "n_reentry": fate_n["REENTRY"],
        "n_reverse": fate_n["REVERSE"],
        "n_censor": fate_n["CENSOR"],
        "resume_rate": round(fate_n["RESUME"] / n, 6) if n else None,
        "hours_to_fate_p50": hours[n // 2] if hours else None,
        "blocked": "无 EMA/OF。不准放宽三买。9 vs 11 不是本枪对照。PULLBACK_IN 不是命运对照臂。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_3RD_POINT_FATE_001  decision={decision}  kind={kind}",
        "15m 离开 → 第一笔回抽不回中枢 → 三买之后命运。无 EMA。",
        "",
        f"  漏斗  leave={N_LEAVE} → pullback_in={N_PULLBACK_IN} → n_3={n}",
        f"  fate  RESUME={fate_n['RESUME']} REENTRY={fate_n['REENTRY']} "
        f"REVERSE={fate_n['REVERSE']} CENSOR={fate_n['CENSOR']}",
        f"  resume_rate={result['resume_rate']} hours_p50={result['hours_to_fate_p50']}",
        f"  clock_ok={clock_ok}",
        "",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
