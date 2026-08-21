"""CHAN_EMA52_STATE_001. State-modulated EMA52 location. No OF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_ema52_state.audit import audit
from chan_ema52_state.paths import EXPECTED_N_15M, KLINE_1M, LOG
from chan_ema52_state.scan import label_htf, scan_trend_pullbacks
from chan_fractal_of.clock import resample_bars


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    k1 = pd.read_parquet(KLINE_1M)
    bar_15 = resample_bars(k1, 15)
    bar_1h = resample_bars(k1, 60)
    states, zids = label_htf(bar_1h)
    episodes = scan_trend_pullbacks(bar_1h, states, zids)
    result = audit(states, episodes, n_1h=len(bar_1h))
    if len(bar_15) != EXPECTED_N_15M:
        result["decision"] = "FAIL"
        result["kind"] = "CLOCK"
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    dump = []
    for e in episodes:
        dump.append(
            {
                "side": e["side"],
                "state_at_swing": e["state_at_swing"],
                "T_SWING_VISIBLE": e["T_SWING_VISIBLE"],
                "T_CHECKPOINT": e.get("T_CHECKPOINT"),
                "T_END": e["T_END"],
                "bucket": e.get("bucket"),
                "fate": e["fate"],
                "end_state": e.get("end_state"),
                "min_dist_atr": None if e.get("min_dist_atr") is None else round(e["min_dist_atr"], 4),
                "hours_to_end": e["hours_to_end"],
            }
        )
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(x, default=str) for x in dump) + ("\n" if dump else "")
    )
    lines = [
        f"CHAN_EMA52_STATE_001  decision={result['decision']}  kind={result['kind']}",
        "Trend 内 NEAR vs FAR。RANGE 穿越不进对照。EMA 参数同 WHERE_001。",
        "",
        f"  n_1h={result['n_1h']} RANGE={result['n_range']} TRANS={result['n_transition']} "
        f"UP={result['n_trend_up']} DOWN={result['n_trend_down']} NONE={result['n_none']}",
        f"  n_episode={result['n_episode']} checkpoint={result['n_checkpoint']}",
        f"  NEAR={result['n_near']} MID={result['n_mid']} FAR={result['n_far']} CROSS={result['n_cross']}",
        f"  near_resume={result['near_resume']} far_resume={result['far_resume']}",
        f"  near_reentry={result['near_reentry']} far_reentry={result['far_reentry']}",
        f"  near_hours_p50={result['near_hours_p50']} far_hours_p50={result['far_hours_p50']}",
        f"  fate={result['fate_all']} clock_ok={result['clock_ok']}",
        "",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
