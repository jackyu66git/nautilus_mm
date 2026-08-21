"""CHAN_TRADE_OF_001 Phase 2. Mechanism vs artifact. Same 15m events."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_trade_of.audit_p2 import audit_phase2
from chan_trade_of.paths import LOG


def main() -> None:
    src = LOG / "PHASE_0_EVENTS.jsonl"
    rows = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    result = audit_phase2(rows)
    (LOG / "PHASE_2_INVENTORY.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        f"CHAN_TRADE_OF_001 Phase 2  decision={result['decision']}  kind={result['kind']}",
        f"n_fx={result['n_events']}  15m forming + aggTrades",
        "MECHANISM_STABLE / CONDITIONAL_MECHANISM / ARTIFACT  — 均不进交易层",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "PHASE_2_INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
