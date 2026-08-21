"""CHAN_HTF_ZS_LTF_B1_001 Phase 0. Timing/space only. No economics. No SMC. No OF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_htf_zs_ltf_b1.audit_p0 import audit_phase0
from chan_htf_zs_ltf_b1.paths import KLINE_1M, LOG
from chan_htf_zs_ltf_b1.replay import build_phase0


def _jsonable(x):
    if isinstance(x, pd.Timestamp):
        return str(x)
    return x


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    kline = pd.read_parquet(KLINE_1M)
    rows = build_phase0(kline)
    result = audit_phase0(rows)
    (LOG / "PHASE_0_INVENTORY.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (LOG / "PHASE_0_EVENTS.jsonl").write_text(
        "\n".join(json.dumps({k: _jsonable(v) for k, v in r.items()}, default=str) for r in rows)
        + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_HTF_ZS_LTF_B1_001 Phase 0  decision={result['decision']}  kind={result['kind']}",
        "1H ZS × 15m B1_LOCK  时序/空间审计。不比较 B1→B2。不接 OF/SMC",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    s = result.get("summary") or {}
    if s:
        lines.append("")
        for k, v in s.items():
            lines.append(f"  {k}={v}")
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "PHASE_0_INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
