"""CHAN_FX_BI_TRADE_OF_001. Join existing ledgers. No B1/B2. No trade rescan."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_fx_bi_trade_of.audit import audit, join_ledgers
from chan_fx_bi_trade_of.paths import FX_EVENTS, LOG, TRADE_EVENTS


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    trade_rows = _load(TRADE_EVENTS)
    fx_rows = _load(FX_EVENTS)
    rows, missing, extra, side_mismatch = join_ledgers(trade_rows, fx_rows)
    result = audit(rows, missing, extra, side_mismatch, require_baseline_n=True)
    slim = {k: v for k, v in result.items() if k != "events"}
    (LOG / "INVENTORY.json").write_text(json.dumps(slim, indent=2, default=str) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in rows) + ("\n" if rows else "")
    )
    s = result.get("summary") or {}
    lines = [
        f"CHAN_FX_BI_TRADE_OF_001  decision={result['decision']}  kind={result['kind']}",
        f"n_fx={result['n_events']} bottom={result['n_bottom']} ordinary={result['n_ordinary']} bi={result['n_bi']}",
        "15m same events. OF = forming aggTrades. ≠ B1/B2",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    if s:
        lines.append("")
        if "base_rate" in s:
            lines.append(f"  base_rate={s['base_rate']:.4f}")
        for key in ("topk_delta", "topk_hhi", "topk_push"):
            if key in s:
                lines.append(f"  {key}={s[key]}")
        for key in ("cliff_delta", "cliff_hhi", "cliff_push", "auc_delta_lower"):
            if key in s:
                lines.append(f"  {key}={s[key]}")
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "INVENTORY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
