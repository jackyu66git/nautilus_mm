"""CHAN_CONT_PERSIST_001. H=1..4 chain vs Null. No EMA. B1/B2/B3 HOLD."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_cont_null.scan import BUY, event_index, load_events
from chan_cont_persist.paths import (
    DELTA_NO_INCREMENT,
    E1,
    E2,
    E3,
    EXPECTED_H1_EXTEND,
    EXPECTED_N_EVENT,
    EXPECTED_N_15M,
    HORIZONS,
    KLINE_1M,
    LOG,
)
from chan_cont_persist.scan import chain_ok, null_chain_rates
from chan_fractal_of.clock import resample_bars

FAMILY = {"B1": "B1", "S1": "B1", "B2": "B2", "S2": "B2", "B3": "B3", "S3": "B3"}


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
        rec = {"event_id": ev["event_id"], "kind": ev["kind"], "side": side, "tape_row": i}
        for h in HORIZONS:
            rec[f"C{h}"] = chain_ok(high, low, i, side, h)
        rows.append(rec)

    n = len(rows)
    n_buy = sum(1 for r in rows if r["side"] == "BUY")
    n_sell = n - n_buy
    by_h = {}
    for h in HORIZONS:
        null = null_chain_rates(high, low, skip, h)
        n_hit = sum(1 for r in rows if r[f"C{h}"])
        rate = n_hit / n if n else None
        mix = (
            (n_buy * null["p_up"] + n_sell * null["p_down"]) / n
            if n and null["p_up"] is not None
            else None
        )
        delta = round(rate - mix, 6) if rate is not None and mix is not None else None
        fam = defaultdict(lambda: {"n": 0, "hit": 0})
        for r in rows:
            f = FAMILY[r["kind"]]
            fam[f]["n"] += 1
            fam[f]["hit"] += int(r[f"C{h}"])
        by_h[h] = {
            "n_hit": n_hit,
            "event_rate": round(rate, 6) if rate is not None else None,
            "mix_null": round(mix, 6) if mix is not None else None,
            "delta": delta,
            "null_n": null["n_null"],
            "null_p_up": null["p_up"],
            "null_p_down": null["p_down"],
            "by_family": {
                f: {"n": v["n"], "hit": v["hit"], "rate": round(v["hit"] / v["n"], 6)}
                for f, v in fam.items()
            },
        }

    h1, h2 = by_h[1], by_h[2]
    if len(bar) != EXPECTED_N_15M or missing or n != EXPECTED_N_EVENT:
        decision, kind = "FAIL", "CLOCK"
    elif h1["n_hit"] != EXPECTED_H1_EXTEND:
        decision, kind = "FAIL", "CLOCK"
    elif h1["delta"] is None or h1["delta"] < DELTA_NO_INCREMENT:
        decision, kind = "FAIL", "NO_INCREMENT"
    elif h2["delta"] is None or h2["delta"] < DELTA_NO_INCREMENT:
        decision, kind = "PASS", "ONE_BAR_ARTIFACT"
    else:
        decision, kind = "PASS", "PERSISTENCE"

    result = {
        "decision": decision,
        "kind": kind,
        "n_15m": len(bar),
        "n_event": n,
        "n_buy": n_buy,
        "n_sell": n_sell,
        "horizons": HORIZONS,
        "by_h": by_h,
        "y": "chain high[i+k]>high[i+k-1] (buy). not vs T0 only. not Fate.",
        "blocked": "B1/B2/B3 HOLD。无 EMA/OF/Trend Age。不准优化 H。不准合桶当 Alpha。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + ("\n" if rows else "")
    )
    lines = [
        f"CHAN_CONT_PERSIST_001  decision={decision}  kind={kind}",
        "链 continuation vs Null。H=1,2,3,4 预注册。B1/B2/B3 只读。",
        "",
    ]
    for h in HORIZONS:
        d = by_h[h]
        fam = "  ".join(
            f"{f}={v['hit']}/{v['n']}={v['rate']}" for f, v in sorted(d["by_family"].items())
        )
        pp = None if d["delta"] is None else round(d["delta"] * 100, 1)
        lines.append(
            f"  H{h}  event={d['n_hit']}/{n}={d['event_rate']}  "
            f"mix_null={d['mix_null']}  delta={d['delta']} ({pp}pp)"
        )
        lines.append(f"      {fam}")
    lines += [
        "",
        "Y=连续原方向扩展链。H1 必须=27/47。比较不用 Fate。",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
