"""CHAN_3BUY_15M_UNIVERSE_001. Independent 15m vs 1H 3rd-point counts. No EMA."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_3buy_15m_universe.paths import EXPECTED_N_15M, FROZEN_15M, FROZEN_N_3, KLINE_1M, LOG
from chan_3buy_15m_universe.scan import scan_third_tf
from chan_fractal_of.clock import resample_bars


def _ids(path: Path) -> set[str]:
    return {json.loads(l)["event_id"] for l in path.read_text().splitlines() if l}


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    k1 = pd.read_parquet(KLINE_1M)
    bar_15 = resample_bars(k1, 15)
    bar_1h = resample_bars(k1, 60)
    frozen = _ids(FROZEN_15M)
    u15 = scan_third_tf(bar_15, "15m")
    u1h = scan_third_tf(bar_1h, "1h")
    live15 = {e["event_id"] for e in u15["events"]}
    match = live15 == frozen
    clock_ok = len(bar_15) == EXPECTED_N_15M and len(frozen) == FROZEN_N_3
    if not clock_ok:
        decision, kind = "FAIL", "CLOCK"
    else:
        decision, kind = "PASS", "UNIVERSE_OK"
    result = {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "n_1h_bars": u1h["n_bars"],
        "n_1h_zs": u1h["n_zs"],
        "n_1h_leave": u1h["n_leave"],
        "n_1h_b3": u1h["n_b3"],
        "n_1h_s3": u1h["n_s3"],
        "n_1h_3": u1h["n_3"],
        "n_15m_bars": u15["n_bars"],
        "n_15m_zs": u15["n_zs"],
        "n_15m_leave": u15["n_leave"],
        "n_15m_b3": u15["n_b3"],
        "n_15m_s3": u15["n_s3"],
        "n_15m_3": u15["n_3"],
        "frozen_n_3": len(frozen),
        "regen_15m_equals_frozen": match,
        "n_only_regen": len(live15 - frozen),
        "n_only_frozen": len(frozen - live15),
        "blocked": "无 EMA/OF。不准改三买定义。不准改 CHAN_3BUY_EMA52_001 的 9 vs 11。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS_15M.jsonl").write_text(
        "\n".join(json.dumps(e) for e in u15["events"]) + ("\n" if u15["events"] else "")
    )
    (LOG / "EVENTS_1H.jsonl").write_text(
        "\n".join(json.dumps(e) for e in u1h["events"]) + ("\n" if u1h["events"] else "")
    )
    lines = [
        f"CHAN_3BUY_15M_UNIVERSE_001  decision={decision}  kind={kind}",
        "冻结定义，15m 与 1H 独立重识别。无 EMA。",
        "",
        f"  1H  n_bars={u1h['n_bars']} n_zs={u1h['n_zs']} n_leave={u1h['n_leave']} "
        f"B3={u1h['n_b3']} S3={u1h['n_s3']} n_3={u1h['n_3']}",
        f"  15m n_bars={u15['n_bars']} n_zs={u15['n_zs']} n_leave={u15['n_leave']} "
        f"B3={u15['n_b3']} S3={u15['n_s3']} n_3={u15['n_3']}",
        f"  frozen_15m_events={len(frozen)} regen_equals_frozen={match}",
        f"  only_regen={len(live15 - frozen)} only_frozen={len(frozen - live15)}",
        "",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
