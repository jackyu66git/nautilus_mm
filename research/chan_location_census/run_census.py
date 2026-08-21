"""CHAN_LOCATION_CENSUS_001. T0 vs ZS box. No ATR. No EMA. Continuation Y frozen."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_cont_null.scan import load_events
from chan_fractal_of.clock import resample_bars
from chan_location_census.paths import (
    CELL_MIN,
    CONT,
    E1,
    E2,
    E3,
    E3_MOTHER,
    EXPECTED_H1_EXTEND,
    EXPECTED_N_EVENT,
    EXPECTED_N_15M,
    KLINE_1M,
    LOG,
)
from chan_location_census.scan import boxes_from_scans, pos_of, region

FAMILY = {"B1": "B1", "S1": "B1", "B2": "B2", "S2": "B2", "B3": "B3", "S3": "B3"}


def _q(xs: list[float]) -> dict | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)

    def at(p):
        return s[min(n - 1, int(p * (n - 1)))]

    return {"n": n, "min": round(s[0], 4), "p25": round(at(0.25), 4), "p50": round(at(0.5), 4), "p75": round(at(0.75), 4), "max": round(s[-1], 4)}


def _rate(rows, pred) -> dict:
    hit = [r for r in rows if pred(r)]
    n = len(hit)
    k = sum(1 for r in hit if r["t1"])
    return {"n": n, "t1": k, "rate": round(k / n, 6) if n else None}


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    y = {e["event_id"]: e for e in load_events(CONT)}
    mother3 = {e["event_id"]: e for e in load_events(E3_MOTHER)}
    boxes = boxes_from_scans(bar)
    fate = load_events(E1, E2, E3)
    rows = []
    missing_box = missing_y = 0
    for ev in fate:
        eid = ev["event_id"]
        kind = ev["kind"]
        if eid not in y:
            missing_y += 1
            continue
        if kind in ("B3", "S3"):
            box = mother3.get(eid)
        else:
            box = boxes.get(eid)
        if box is None or "zg" not in box:
            missing_box += 1
            continue
        i = int(y[eid]["tape_row"])
        px = float(bar.iloc[i]["close"])
        zg, zd = float(box["zg"]), float(box["zd"])
        pos = pos_of(px, zg, zd)
        if pos is None:
            missing_box += 1
            continue
        rows.append(
            {
                "event_id": eid,
                "kind": kind,
                "family": FAMILY[kind],
                "zg": zg,
                "zd": zd,
                "close": px,
                "pos": round(pos, 6),
                "region": region(pos),
                "t1": bool(y[eid]["next_bar_extend"]),
                "tape_row": i,
            }
        )

    n = len(rows)
    n_t1 = sum(1 for r in rows if r["t1"])
    n_in = sum(1 for r in rows if r["region"] == "IN")
    both_ok = n_in >= CELL_MIN and (n - n_in) >= CELL_MIN
    fam_split = {}
    for f in ("B1", "B2", "B3"):
        sub = [r for r in rows if r["family"] == f]
        inn = sum(1 for r in sub if r["region"] == "IN")
        fam_split[f] = inn >= CELL_MIN and (len(sub) - inn) >= CELL_MIN
    if len(bar) != EXPECTED_N_15M or missing_y or n != EXPECTED_N_EVENT:
        decision, kind = "FAIL", "CLOCK"
    elif n_t1 != EXPECTED_H1_EXTEND:
        decision, kind = "FAIL", "CLOCK"
    elif missing_box:
        decision, kind = "FAIL", "BOX"
    elif not both_ok:
        decision, kind = "PASS", "HOLD_NO_SPLIT"
    else:
        decision, kind = "PASS", "CENSUS_OK"

    by_reg = {k: _rate(rows, lambda r, x=k: r["region"] == x) for k in ("IN", "OUT_HIGH", "OUT_LOW")}
    by_fam = {}
    for f in ("B1", "B2", "B3"):
        sub = [r for r in rows if r["family"] == f]
        by_fam[f] = {
            "n": len(sub),
            "region": dict(Counter(r["region"] for r in sub)),
            "pos": _q([r["pos"] for r in sub]),
            "t1_in": _rate(sub, lambda r: r["region"] == "IN"),
            "t1_out": _rate(sub, lambda r: r["region"] != "IN"),
            "split_ok": fam_split[f],
        }
    result = {
        "decision": decision,
        "kind": kind,
        "n_event": n,
        "n_t1": n_t1,
        "n_in": n_in,
        "cell_min": CELL_MIN,
        "in_out_split_ok": both_ok,
        "by_region": by_reg,
        "by_family": by_fam,
        "pos_all": _q([r["pos"] for r in rows]),
        "t1_in": _rate(rows, lambda r: r["region"] == "IN"),
        "t1_out": _rate(rows, lambda r: r["region"] != "IN"),
        "blocked": "无 ATR 分桶。无 EMA/OF。Continuation CLOSED。n<5 不开 Location Modifier。",
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    lines = [
        f"CHAN_LOCATION_CENSUS_001  decision={decision}  kind={kind}",
        "T0 相对冻结中枢盒子。无 ATR。无 EMA。T+1=纯 continuation。",
        "",
        f"  n={n} t1={n_t1} IN={n_in} OUT={n - n_in}  pos={result['pos_all']}",
        f"  region IN={by_reg['IN']} OUT_HIGH={by_reg['OUT_HIGH']} OUT_LOW={by_reg['OUT_LOW']}",
        f"  t1 IN={result['t1_in']} OUT={result['t1_out']}",
        "",
    ]
    for f, d in by_fam.items():
        lines.append(
            f"  {f} n={d['n']} region={d['region']} pos_p50={None if not d['pos'] else d['pos']['p50']} "
            f"t1_in={d['t1_in']} t1_out={d['t1_out']} split_ok={d['split_ok']}"
        )
    lines += ["", "不准 ATR/NEAR。n<5 则 Location HOLD。不因本枪开 EMA52。", result["blocked"]]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
