"""CHAN_HTF_HIST_ANCHOR_LTF_B1_001 Phase 0. Q1–Q3 only. No Q4."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_htf_hist_anchor.audit_p0 import audit_phase0
from chan_htf_hist_anchor.paths import KLINE_1M, LOG, LTF_B1_EVENTS
from chan_htf_hist_anchor.replay import build_phase0, replay_ltf_b1_lock
from chan_fractal_of.clock import resample_bars


def _jsonable(x):
    if isinstance(x, pd.Timestamp):
        return str(x)
    return x


def _load_ltf() -> list[dict] | None:
    if not LTF_B1_EVENTS.exists():
        return None
    rows = [json.loads(line) for line in LTF_B1_EVENTS.read_text().splitlines() if line.strip()]
    seen = []
    got = set()
    for r in rows:
        k = r["LTF_B1"]
        if k in got:
            continue
        got.add(k)
        seen.append(
            {
                "LTF_B1": r["LTF_B1"],
                "T_LTF_B1": r["T_LTF_B1"],
                "B1_bar": r.get("B1_bar"),
                "leave_low": r["leave_low"],
                "leave_high": r["leave_high"],
            }
        )
    return seen


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    kline = pd.read_parquet(KLINE_1M)
    ltf = _load_ltf()
    if ltf is None:
        print("LTF B1 ledger missing; replaying 15m B1_LOCK", flush=True)
        ltf = replay_ltf_b1_lock(resample_bars(kline, 15))
    else:
        print(f"reuse LTF B1_LOCK n={len(ltf)} from CHAN_HTF_ZS_LTF_B1_001", flush=True)
    rows = build_phase0(kline, ltf_rows=ltf)
    result = audit_phase0(rows)
    (LOG / "PHASE_0_INVENTORY.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (LOG / "PHASE_0_EVENTS.jsonl").write_text(
        "\n".join(json.dumps({k: _jsonable(v) for k, v in r.items()}, default=str) for r in rows)
        + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_HTF_HIST_ANCHOR_LTF_B1_001 Phase 0  decision={result['decision']}  kind={result['kind']}",
        "leftover 1H zg/zd/gg/dd × 15m B1_LOCK。living 盒子不是对象。Q4 未跑。",
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
