"""CHAN_TRADE_OF_001 Phase 0. 15m fractal + aggTrades. No 5m. No absorption detector."""
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
from chan_fractal_of.of_window import load_of_1m
from chan_trade_of.audit import audit
from chan_trade_of.paths import KLINE_1M, LOG, OF_1M
from chan_trade_of.trades import load_trade_store


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    kline = pd.read_parquet(KLINE_1M)
    bar = resample_15m(kline)
    of = load_of_1m(OF_1M)
    print("clock 15m...", flush=True)
    state = replay_fractal_clock(bar)
    print(f"fx={len(state.events)}  load trades...", flush=True)
    trades = load_trade_store()
    print(f"trades n={len(trades.ts)}", flush=True)
    result = audit(state, of, trades)
    (LOG / "PHASE_0_INVENTORY.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2, default=str) + "\n"
    )
    (LOG / "PHASE_0_EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in result["events"]) + ("\n" if result["events"] else "")
    )
    lines = [
        f"CHAN_TRADE_OF_001 Phase 0  decision={result['decision']}  kind={result['kind']}",
        f"scale=15m fractal + aggTrades  n_15m={result['n_15m']} n_fx={result['n_events']}",
        "STRATA 15m=CLOSED/NO_GRADIENT (kline proxy only)",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    if result.get("summary"):
        lines.append("")
        for k, v in result["summary"].items():
            lines.append(f"  {k}={v}")
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "PHASE_0_INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
