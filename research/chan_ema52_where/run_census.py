"""CHAN_EMA52_WHERE_001 Layer 1. EMA52 WHERE only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_ema52_where.audit import audit
from chan_ema52_where.paths import EXPECTED_N_15M, KLINE_1M, LOG
from chan_ema52_where.scan import scan_episodes
from chan_fractal_of.clock import resample_bars


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    k1 = pd.read_parquet(KLINE_1M)
    bar_15 = resample_bars(k1, 15)
    bar_1h = resample_bars(k1, 60)
    episodes = scan_episodes(bar_1h)
    result = audit(episodes, n_1h=len(bar_1h))
    if len(bar_15) != EXPECTED_N_15M:
        result["decision"] = "FAIL"
        result["kind"] = "CLOCK"
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    dump = []
    for e in episodes:
        dump.append(
            {
                "side": e["side"],
                "T_SWING_VISIBLE": e["T_SWING_VISIBLE"],
                "T_NEAR_VISIBLE": e["T_NEAR_VISIBLE"],
                "T_CHECKPOINT": e.get("T_CHECKPOINT"),
                "T_END": e["T_END"],
                "fate": e["fate"],
                "near": bool(e["near"]),
                "checkpoint": e.get("checkpoint"),
                "away_atr": round(e["away_atr"], 4),
                "near_dist_atr": None if e["near_dist_atr"] is None else round(e["near_dist_atr"], 4),
                "hours_to_end": e["hours_to_end"],
            }
        )
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(x, default=str) for x in dump) + ("\n" if dump else "")
    )
    lines = [
        f"CHAN_EMA52_WHERE_001  decision={result['decision']}  kind={result['kind']}",
        "1H EMA52 = WHERE。回撤到均线附近 vs 仍远离。无 MACD / 三买 / 收益。",
        "",
        f"  n_1h={result['n_1h']} n_episode={result['n_episode']} up={result['n_up']} down={result['n_down']}",
        f"  n_near={result['n_near']} n_never_near={result['n_never_near']}",
        f"  fate resume={result['n_resume']} break={result['n_break']} censor={result['n_censor']}",
        f"  near_resume={result['near_resume_rate']} near_break={result['near_break_rate']}",
        f"  checkpoint NEAR n={result['n_checkpoint_near']} resume={result['checkpoint_near_resume_rate']}",
        f"  checkpoint FAR  n={result['n_checkpoint_far']} resume={result['checkpoint_far_resume_rate']}",
        f"  clock_ok={result['clock_ok']}",
        "",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
