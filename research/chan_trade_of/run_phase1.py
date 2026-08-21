"""CHAN_TRADE_OF_001 Phase 1. Same 15m events as Phase 0. No 5m. No absorption."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
CHAN = Path("/Users/jack/Project/freqtrade/user_data/Chan")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(CHAN))

from chan_trade_of.audit_p1 import audit_phase1
from chan_trade_of.paths import LOG


def main() -> None:
    src = LOG / "PHASE_0_EVENTS.jsonl"
    rows = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    result = audit_phase1(rows)
    (LOG / "PHASE_1_INVENTORY.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        f"CHAN_TRADE_OF_001 Phase 1  decision={result['decision']}  kind={result['kind']}",
        f"n_fx={result['n_events']}  15m forming + aggTrades  (same events as Phase 0)",
        "NEW_DIMENSION ≠ NEW_EDGE",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    s = result.get("summary") or {}
    if s:
        lines.append("")
        lines.append(
            f"rho_raw={s.get('rho_raw')} rho_resid={s.get('rho_resid')} inc_R2={s.get('inc_R2')}"
        )
        lines.append(
            f"halves={s.get('rho_half_a')} / {s.get('rho_half_b')}  "
            f"bottom/top={s.get('rho_bottom')} / {s.get('rho_top')}"
        )
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "PHASE_1_INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
