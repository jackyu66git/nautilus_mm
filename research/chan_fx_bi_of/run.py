"""CHAN_FX_BI_OF_001. Same 15m+1m scale. No B1/B2."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
CHAN = Path("/Users/jack/Project/freqtrade/user_data/Chan")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(CHAN))

from chan_fractal_of.clock import replay_fractal_clock, resample_15m
from chan_fractal_of.labels import bars_to_label_engine
from chan_fractal_of.of_window import load_of_1m
from chan_fx_bi_of.audit import audit
from chan_fx_bi_of.paths import KLINE_1M, LOG, OF_1M
from chan_fx_bi_of.truth import extract_bi_only


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    kline = pd.read_parquet(KLINE_1M)
    bar = resample_15m(kline)
    of = load_of_1m(OF_1M)
    state = replay_fractal_clock(bar)
    engine = bars_to_label_engine(bar)
    truth = extract_bi_only(engine)
    result = audit(state, of, truth)
    (LOG / "INVENTORY.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2, default=str) + "\n"
    )
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in result["events"]) + ("\n" if result["events"] else "")
    )
    lines = [
        f"CHAN_FX_BI_OF_001  decision={result['decision']}",
        f"scale=15m Fractal + 1m OF  n_15m={result['n_15m']} n_klc={result['n_klc']} n_fx={result['n_events']}",
        f"sure_bi={result['truth']['n_sure_bi']} unsure_bi={result['truth']['n_unsure_bi']} "
        f"endpoints={result['truth']['n_endpoints']}",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    if result["summary"]:
        lines.append("")
        for k, v in result["summary"].items():
            if k == "unused_features":
                continue
            lines.append(f"  {k}={v}")
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
