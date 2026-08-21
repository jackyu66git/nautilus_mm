"""CHAN_3BUY_EMA52_001. Frozen 15m 3rd points × EMA52 pullback. No OF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_3buy_ema52.audit import audit
from chan_3buy_ema52.paths import EXPECTED_N_15M, EXPECTED_N_3, KLINE_1M, LOG, MOTHER
from chan_3buy_ema52.scan import follow_all
from chan_fractal_of.clock import resample_bars


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    events = [json.loads(l) for l in MOTHER.read_text().splitlines() if l]
    bar_15 = resample_bars(pd.read_parquet(KLINE_1M), 15)
    rows = follow_all(events, bar_15)
    result = audit(rows, n_mother=len(events))
    if len(bar_15) != EXPECTED_N_15M or len(events) != EXPECTED_N_3:
        result["decision"] = "FAIL"
        result["kind"] = "CLOCK"
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in rows) + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_3BUY_EMA52_001  decision={result['decision']}  kind={result['kind']}",
        "15m 三买/三卖之后，回撤是否进入 EMA52 附近。命运不是涨跌。",
        "",
        f"  n_mother={result['n_mother']} B3={result['n_b3']} S3={result['n_s3']} no_pb={result['n_no_pb']}",
        f"  usable={result['n_usable']} entered={result['n_entered']} not_entered={result['n_not_entered']}",
        f"  entered_resume={result['entered_resume']} missed_resume={result['missed_resume']}",
        f"  entered_reentry={result['entered_reentry']} missed_reentry={result['missed_reentry']}",
        f"  fate={result['fate_all']} clock_ok={result['clock_ok']}",
        "",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
