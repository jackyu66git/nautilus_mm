"""CHAN_BI_OF_STRATA_005M_001. Same protocol as 15m. Structure TF = 5m only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
CHAN = Path("/Users/jack/Project/freqtrade/user_data/Chan")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(CHAN))

from chan_bi_of_strata.audit import audit
from chan_bi_of_strata.endpoints import extract_confirmed_endpoints
from chan_bi_of_strata_5m.paths import BAR_MINUTES, KLINE_1M, LOG, OF_1M
from chan_fractal_of.clock import replay_fractal_clock, resample_bars
from chan_fractal_of.labels import bars_to_label_engine
from chan_fractal_of.of_window import load_of_1m


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    kline = pd.read_parquet(KLINE_1M)
    bar = resample_bars(kline, BAR_MINUTES)
    of = load_of_1m(OF_1M)
    state = replay_fractal_clock(bar, bar_minutes=BAR_MINUTES)
    engine = bars_to_label_engine(bar)
    ends = extract_confirmed_endpoints(engine, bar_minutes=BAR_MINUTES)
    result = audit(
        state,
        bar,
        of,
        ends,
        experiment="CHAN_BI_OF_STRATA_005M_001",
        scale="5m bi-endpoint + 1m OF",
    )
    (LOG / "INVENTORY.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2, default=str) + "\n"
    )
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in result["events"]) + ("\n" if result["events"] else "")
    )
    lines = [
        f"CHAN_BI_OF_STRATA_005M_001  decision={result['decision']}  kind={result['kind']}",
        f"scale=5m bi-endpoint + 1m OF  n_bars={result['n_15m']} n_ep={result['n_events']}",
        "15m predecessor=CHAN_BI_OF_STRATA_001 FAIL/NO_GRADIENT (immutable)",
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
