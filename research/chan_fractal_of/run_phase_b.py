"""CHAN_FRACTAL_OF_001 Phase B. Same 15m+1m scale as A. Labels overlay only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
CHAN = Path("/Users/jack/Project/freqtrade/user_data/Chan")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(CHAN))

from chan_fractal_of.audit_b import audit_b
from chan_fractal_of.clock import replay_fractal_clock, resample_15m
from chan_fractal_of.labels import bars_to_label_engine, extract_truth
from chan_fractal_of.of_window import load_of_1m
from chan_fractal_of.paths import KLINE_1M, LOG, OF_1M


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    kline = pd.read_parquet(KLINE_1M)
    bar = resample_15m(kline)
    of = load_of_1m(OF_1M)
    state = replay_fractal_clock(bar)
    engine = bars_to_label_engine(bar)
    truth = extract_truth(engine)
    result = audit_b(state, of, truth)
    (LOG / "PHASE_B_INVENTORY.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2, default=str) + "\n"
    )
    (LOG / "PHASE_B_EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in result["events"]) + ("\n" if result["events"] else "")
    )
    lines = [
        f"CHAN_FRACTAL_OF_001 Phase B  decision={result['decision']}",
        f"scale=15m Fractal + 1m OF  n_15m={result['n_15m']} n_klc={result['n_klc']} n_fx={result['n_events']}",
        f"truth n_sure_bi={result['truth']['n_sure_bi']} n_zs={result['truth']['n_zs_sure']} "
        f"n_b1={result['truth']['n_b1']} n_b2={result['truth']['n_b2']} n_b1_b2_fx={result['truth']['n_b1_b2_fx']}",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    if result["summary"]:
        lines.append("")
        for k, v in result["summary"].items():
            lines.append(f"  {k}={v}")
    lines.append("")
    lines.append(result["blocked"])
    out_txt = LOG / "PHASE_B_INVENTORY.txt"
    out_txt.write_text("\n".join(lines) + "\n")
    print(out_txt.read_text())


if __name__ == "__main__":
    main()
