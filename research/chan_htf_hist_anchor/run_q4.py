"""CHAN_HTF_HIST_ANCHOR_LTF_B1_001 Q4. B1 unit. No OF/SMC/MACD/P&L."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_fractal_of.clock import resample_bars
from chan_htf_hist_anchor.audit_q4 import (
    audit_q4,
    collapse_to_b1,
    count_matched_contact_rate,
    load_b2_from_early,
)
from chan_htf_hist_anchor.paths import EARLY_CASES, KLINE_1M, LOG, PHASE0_EVENTS
from chan_htf_hist_anchor.replay import replay_htf_hist


def _jsonable(x):
    if isinstance(x, pd.Timestamp):
        return str(x)
    return x


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    pair_rows = [json.loads(line) for line in PHASE0_EVENTS.read_text().splitlines() if line.strip()]
    b2 = load_b2_from_early(EARLY_CASES)
    b1_rows = collapse_to_b1(pair_rows, b2)
    print(f"Q4 unit B1 n={len(b1_rows)} from pair rows={len(pair_rows)}", flush=True)

    kline = pd.read_parquet(KLINE_1M)
    bar_15m = resample_bars(kline, 15)
    bar_1h = resample_bars(kline, 60)
    book = replay_htf_hist(bar_1h)
    b1_closes = {r["T_LTF_B1"] for r in b1_rows}
    print("Q4 count-matched 15m baseline", flush=True)
    baseline = count_matched_contact_rate(bar_15m, book, b1_closes)
    result = audit_q4(b1_rows, baseline)

    (LOG / "Q4_INVENTORY.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (LOG / "Q4_EVENTS.jsonl").write_text(
        "\n".join(json.dumps({k: _jsonable(v) for k, v in r.items()}, default=str) for r in b1_rows)
        + ("\n" if b1_rows else "")
    )
    lines = [
        f"CHAN_HTF_HIST_ANCHOR_LTF_B1_001 Q4  decision={result['decision']}  kind={result['kind']}",
        "unit=B1 event。HIST leftover × B1 → B2 overlay。不准 pair 复制 / OF / SMC / MACD / MFE / MAE。",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    s = result.get("summary") or {}
    if s.get("b1"):
        lines.append("")
        lines.append("B1  anchor_count  contact_any  zg zd gg dd  latest_zg/zd/gg/dd  LTF_B2")
        for r in s["b1"]:
            lines.append(
                f"  {r['LTF_B1']}  n={r['anchor_count_at_B1']}  "
                f"any={int(r['contact_any'])}  "
                f"{int(r['zg_contact_any'])}{int(r['zd_contact_any'])}"
                f"{int(r['gg_contact_any'])}{int(r['dd_contact_any'])}  "
                f"{r['latest_side_zg']}/{r['latest_side_zd']}/{r['latest_side_gg']}/{r['latest_side_dd']}  "
                f"B2={int(bool(r['LTF_B2']))}"
            )
    if s.get("by_count"):
        lines.append("")
        lines.append("count-matched  leftover_n  n_B1  B1_contact  n_bars  bar_contact  bar_rate")
        for k, v in s["by_count"].items():
            lines.append(
                f"  n={k}  B1={v.get('n_b1', 0)}/{v.get('n_b1_contact', 0)}  "
                f"bars={v.get('n_bars')} contact={v.get('n_bar_contact')} rate={v.get('bar_rate')}"
            )
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "Q4_INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
