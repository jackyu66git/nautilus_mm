"""CHAN_HTF_ZS_EXPAND_LTF_REV_001. Auto Replay under Research Mandate."""
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
from chan_htf_zs_expand_ltf_rev.paths import EXPECTED_N_15M, KLINE_1M, LOG, TAPE
from chan_htf_zs_expand_ltf_rev.scan import scan_expand, summarize


def _load_tape() -> list[dict]:
    rows = []
    with TAPE.open() as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    tape = _load_tape()
    kline = pd.read_parquet(KLINE_1M)
    bar_15m = resample_bars(kline, 15)
    book = replay_htf_hist(resample_bars(kline, 60))
    rows = scan_expand(tape, bar_15m, book)
    summary = summarize(rows)
    ok = len(tape) == EXPECTED_N_15M and len(rows) == len(tape) - 1
    kinds = {summary["process_kind"], summary["n_bis_kind"]}
    if not ok:
        decision, kind = "FAIL", "CLOCK"
    elif "HAS_CONTRAST" in kinds:
        decision, kind = "PASS", "HAS_CONTRAST"
    elif kinds == {"SAMPLE_INSUFFICIENT"}:
        decision, kind = "FAIL", "SAMPLE_INSUFFICIENT"
    else:
        decision, kind = "FAIL", "NO_STATE_CONTRAST"
    result = {
        "decision": decision,
        "kind": kind,
        "summary": summary,
        "blocked": "位置切面已关。本切面失败则关闭扩张假设。不准接 OF/SMC/交易。",
    }
    (LOG / "EXPAND.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        f"CHAN_HTF_ZS_EXPAND_LTF_REV_001  decision={decision}  kind={kind}",
        "living 1H 中枢 n_bis 扩张 → 下一根 15m 笔方向反转。",
        "",
        f"  n_bar={summary['n_bar']} n_rev={summary['n_rev']} rev_share={summary['rev_share']}",
        f"  process_kind={summary['process_kind']} n_bis_kind={summary['n_bis_kind']}",
        "",
        "  process",
    ]
    for r in summary["process"]:
        lines.append(
            f"    {r['level']} n={r['n']} n_rev={r['n_rev']} rev_share={r['rev_share']} thin={r['thin']}"
        )
    lines.append("  n_bis")
    for r in summary["n_bis"]:
        lines.append(
            f"    {r['level']} n={r['n']} n_rev={r['n_rev']} rev_share={r['rev_share']} thin={r['thin']}"
        )
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "EXPAND.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
