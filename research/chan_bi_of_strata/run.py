"""CHAN_BI_OF_STRATA_001 read-only replay. Same 15m+1m scale."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
CHAN = Path("/Users/jack/Project/freqtrade/user_data/Chan")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(CHAN))

from chan_bi_of_strata.audit import audit
from chan_bi_of_strata.endpoints import extract_confirmed_endpoints
from chan_bi_of_strata.paths import KLINE_1M, LOG, OF_1M
from chan_fractal_of.clock import replay_fractal_clock, resample_15m
from chan_fractal_of.labels import bars_to_label_engine
from chan_fractal_of.of_window import load_of_1m


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    kline = pd.read_parquet(KLINE_1M)
    bar = resample_15m(kline)
    of = load_of_1m(OF_1M)
    state = replay_fractal_clock(bar)
    engine = bars_to_label_engine(bar)
    ends = extract_confirmed_endpoints(engine)
    result = audit(state, bar, of, ends)
    (LOG / "INVENTORY.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2, default=str) + "\n"
    )
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in result["events"]) + ("\n" if result["events"] else "")
    )
    lines = [
        f"CHAN_BI_OF_STRATA_001  decision={result['decision']}  kind={result['kind']}",
        f"scale=15m bi-endpoint + 1m OF  n_15m={result['n_15m']} n_ep={result['n_events']}",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    if result.get("summary"):
        lines.append("")
        med = result["summary"].get("medians")
        if med:
            lines.append("medians Q1→Q5")
            for k, vals in med.items():
                lines.append("  " + k + " " + " ".join(f"{v:.5g}" for v in vals))
        rho = result["summary"].get("rho_median")
        if rho:
            lines.append("rho_median " + " ".join(f"{k}={v:.3f}" for k, v in rho.items()))
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
