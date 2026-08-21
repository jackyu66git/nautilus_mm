"""CHAN_CONT_NULL_001. Weak RESUME vs ordinary 15m bars. B1/B2/B3 HOLD."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_cont_null.paths import DELTA_NO_INCREMENT, E1, E2, E3, EXPECTED_N_15M, KLINE_1M, LOG
from chan_cont_null.scan import BUY, SELL, event_index, load_events, next_extends, null_rates
from chan_fractal_of.clock import resample_bars


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    events = load_events(E1, E2, E3)
    high = bar["high"].to_numpy(float)
    low = bar["low"].to_numpy(float)
    rows = []
    skip: set[int] = set()
    missing = 0
    for ev in events:
        i = event_index(bar, ev)
        if i is None:
            missing += 1
            continue
        skip.add(i)
        side = "BUY" if ev["kind"] in BUY else "SELL"
        raw = next_extends(high, low, i, side)
        rows.append(
            {
                "event_id": ev["event_id"],
                "kind": ev["kind"],
                "side": side,
                "fate": ev["fate"],
                "hours_to_fate": ev["hours_to_fate"],
                "next_bar_fate": ev["hours_to_fate"] == 0.25,
                "next_bar_extend": raw,
                "tape_row": i,
            }
        )
    null = null_rates(high, low, skip)
    n = len(rows)
    n_buy = sum(1 for r in rows if r["side"] == "BUY")
    n_sell = n - n_buy
    n_ext = sum(1 for r in rows if r["next_bar_extend"])
    n_nb_fate = sum(1 for r in rows if r["next_bar_fate"])
    event_rate = n_ext / n if n else None
    mix_null = (
        (n_buy * null["p_up"] + n_sell * null["p_down"]) / n
        if n and null["p_up"] is not None
        else None
    )
    delta = round(event_rate - mix_null, 6) if event_rate is not None and mix_null is not None else None
    by = Counter(r["kind"] for r in rows)
    ext_by = Counter(r["kind"] for r in rows if r["next_bar_extend"])
    if len(bar) != EXPECTED_N_15M or missing:
        decision, kind = "FAIL", "CLOCK"
    elif n != 47:
        decision, kind = "FAIL", "MOTHER_MISMATCH"
    elif delta is None or delta < DELTA_NO_INCREMENT:
        decision, kind = "FAIL", "NO_INCREMENT"
    else:
        decision, kind = "PASS", "STRUCTURE_INCREMENT"
    result = {
        "decision": decision,
        "kind": kind,
        "n_15m": len(bar),
        "n_event": n,
        "n_buy": n_buy,
        "n_sell": n_sell,
        "n_missing_ts": missing,
        "event_next_bar_extend": n_ext,
        "event_next_bar_extend_rate": round(event_rate, 6) if event_rate is not None else None,
        "event_next_bar_fate": n_nb_fate,
        "null_n": null["n_null"],
        "null_p_up": null["p_up"],
        "null_p_down": null["p_down"],
        "mix_null_rate": round(mix_null, 6) if mix_null is not None else None,
        "delta": delta,
        "delta_threshold": DELTA_NO_INCREMENT,
        "n_by_kind": dict(by),
        "extend_by_kind": dict(ext_by),
        "control": "ordinary 15m bars. not breakout/fx/bi.",
        "blocked": "B1/B2/B3 HOLD。无 EMA/OF/Trend Age。不准把局部突破当对照。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_CONT_NULL_001  decision={decision}  kind={kind}",
        "弱 RESUME 谓词 vs 普通 15m K。B1/B2/B3 只读。",
        "",
        f"  n_event={n} buy={n_buy} sell={n_sell}  by={dict(by)}",
        f"  event next-bar extend={n_ext}/{n} = {result['event_next_bar_extend_rate']}",
        f"  event next-bar fate (冻结口径，含REVERSE/REENTRY赛跑)={n_nb_fate}/{n}",
        f"  null n={null['n_null']} p_up={null['p_up']} p_down={null['p_down']}",
        f"  mix_null={result['mix_null_rate']}  delta={delta}  threshold={DELTA_NO_INCREMENT}",
        f"  extend_by_kind={dict(ext_by)}",
        "",
        "对照=非确认K的普通15m。不是局部突破/分型/笔。",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
