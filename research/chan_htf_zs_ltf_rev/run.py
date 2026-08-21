"""CHAN_HTF_ZS_LTF_REV_001. Living 1H ZS state → next 15m bi_dir flip."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_fractal_of.clock import resample_bars
from chan_htf_hist_anchor.replay import replay_htf_hist
from chan_htf_zs_ltf_rev.paths import EXPECTED_N_15M, KLINE_1M, LOG, TAPE
from chan_htf_zs_ltf_rev.scan import scan, summarize


def _load_tape() -> list[dict]:
    rows = []
    with TAPE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    tape = _load_tape()
    kline = pd.read_parquet(KLINE_1M)
    bar_15m = resample_bars(kline, 15)
    bar_1h = resample_bars(kline, 60)
    book = replay_htf_hist(bar_1h)
    rows = scan(tape, bar_15m, book)
    summary = summarize(rows)
    n_tape = len(tape)
    ok = n_tape == EXPECTED_N_15M and len(rows) == n_tape - 1
    result = {
        "decision": "PASS" if ok else "FAIL",
        "kind": "REV_TABLE_OK" if ok else "CLOCK",
        "n_tape": n_tape,
        "summary": summary,
        "blocked": "不是 Setup。不是交易。B1 不是 y。不准接 OF/SMC。",
    }
    (LOG / "REV.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        f"CHAN_HTF_ZS_LTF_REV_001  decision={result['decision']}  kind={result['kind']}",
        "living 1H 中枢位置 → 下一根 15m 笔方向是否反转。",
        "",
        f"  n_tape={n_tape} n_bar={summary['n_bar']} n_rev={summary['n_rev']} rev_share={summary['rev_share']}",
        "",
        "  state n n_rev rev_share label_b1",
    ]
    for r in summary["table"]:
        lines.append(
            f"  {r['state']} {r['n']} {r['n_rev']} {r['rev_share']} {r['label_b1']}"
        )
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "REV.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
