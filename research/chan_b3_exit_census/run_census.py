"""CHAN_B3_EXIT_CENSUS_001. Target distance / time-to-target. No PnL."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_b3_exit_census.paths import (
    A_MIN_HIT,
    DELTA_PP,
    E3_MOTHER,
    EXPECTED_N_15M,
    EXPECTED_N_B3,
    EXPECTED_N_EVENT,
    EXPECTED_N_S3,
    HORIZON_H,
    KLINE_1M,
    LOG,
    R_GRID,
)
from chan_b3_exit_census.scan import scan_one
from chan_cont_null.scan import load_events
from chan_fractal_of.clock import resample_bars


def _q(xs: list[float]) -> dict | None:
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)

    def at(p: float) -> float:
        return round(s[min(n - 1, int(p * (n - 1)))], 4)

    return {"n": n, "min": round(s[0], 4), "p25": at(0.25), "p50": at(0.5), "p75": at(0.75), "max": round(s[-1], 4)}


def _rate(rows: list[dict], r: float, horizon: str) -> dict:
    key = str(r)
    n = len(rows)
    if horizon == "any":
        sts = [row["levels"][key]["status"] for row in rows]
        hours = [row["levels"][key]["hours"] for row in rows if row["levels"][key]["status"] == "HIT"]
    else:
        sts = [row["by_h"][horizon][key] for row in rows]
        hours = [
            row["levels"][key]["hours"]
            for row in rows
            if row["by_h"][horizon][key] == "HIT" and row["levels"][key]["status"] == "HIT"
        ]
    hit = sts.count("HIT")
    stop = sts.count("STOP_FIRST")
    none = sts.count("NONE")
    censor = sts.count("CENSOR")
    return {
        "n": n,
        "hit": hit,
        "stop_first": stop,
        "none": none,
        "censor": censor,
        "hit_rate": round(hit / n, 6) if n else None,
        "hours_to_hit": _q(hours),
    }


def _branch(rows: list[dict]) -> str:
    h24_05 = _rate(rows, 0.5, "24")["hit_rate"] or 0.0
    h24_10 = _rate(rows, 1.0, "24")["hit_rate"] or 0.0
    any_10 = _rate(rows, 1.0, "any")["hit_rate"] or 0.0
    if h24_05 >= A_MIN_HIT and (h24_05 - h24_10) >= DELTA_PP:
        return "A_SMALLER_TARGET"
    if (any_10 - h24_10) >= DELTA_PP:
        return "B_NEED_TIME"
    return "C_NO_GEOMETRY"


def _grid(rows: list[dict]) -> dict:
    out = {}
    for r in R_GRID:
        out[str(r)] = {
            "any": _rate(rows, r, "any"),
            **{str(h): _rate(rows, r, str(h)) for h in HORIZON_H},
        }
    return out


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    events = load_events(E3_MOTHER)
    rows = [scan_one(ev, bar) for ev in events]
    traded = [r for r in rows if r.get("levels")]
    n_b3 = sum(1 for r in traded if r["kind"] == "B3")
    n_s3 = sum(1 for r in traded if r["kind"] == "S3")
    if (
        len(bar) != EXPECTED_N_15M
        or len(events) != EXPECTED_N_EVENT
        or len(traded) != EXPECTED_N_EVENT
        or n_b3 != EXPECTED_N_B3
        or n_s3 != EXPECTED_N_S3
    ):
        decision, kind = "FAIL", "CLOCK"
    else:
        decision, kind = "PASS", _branch(traded)

    all_g = _grid(traded)
    b3_g = _grid([r for r in traded if r["kind"] == "B3"])
    s3_g = _grid([r for r in traded if r["kind"] == "S3"])
    result = {
        "decision": decision,
        "kind": kind,
        "n_event": len(traded),
        "n_b3": n_b3,
        "n_s3": n_s3,
        "r_grid": list(R_GRID),
        "horizon_h": list(HORIZON_H),
        "delta_pp": DELTA_PP,
        "a_min_hit": A_MIN_HIT,
        "mfe_r": _q([r["mfe_r"] for r in traded]),
        "mfe_24h_r": _q([r["mfe_24h_r"] for r in traded]),
        "mfe_48h_r": _q([r["mfe_48h_r"] for r in traded]),
        "mfe_72h_r": _q([r["mfe_72h_r"] for r in traded]),
        "hours_to_stop": _q([r["hours_to_stop"] for r in traded if r.get("hours_to_stop") is not None]),
        "hours_available": _q([r["hours_available"] for r in traded]),
        "all": all_g,
        "B3": b3_g,
        "S3": s3_g,
        "blocked": (
            "无 EMA/OF/ATR。无 PnL。不改 Entry/Stop。"
            "A → V2 0.5/0.75/1R 另授权。"
            "B → 24/48/72h 另授权。"
            "C → 停三买交易线。不准加指标救。"
            "V1 −0.58R 不是 Economic FAIL。"
        ),
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def cell(g: dict, r: float, hz: str) -> str:
        d = g[str(r)][hz]
        p50 = None if not d["hours_to_hit"] else d["hours_to_hit"]["p50"]
        return f"hit={d['hit']}/{d['n']}={d['hit_rate']} stop={d['stop_first']} none={d['none']} h_p50={p50}"

    lines = [
        f"CHAN_B3_EXIT_CENSUS_001  decision={decision}  kind={kind}",
        "Entry/Stop 冻结。R 网格 × 24/48/72h + 至 Stop/样本末。无 PnL。",
        "",
        f"  mfe_r={result['mfe_r']}",
        f"  mfe_24/48/72={result['mfe_24h_r']['p50']}/{result['mfe_48h_r']['p50']}/{result['mfe_72h_r']['p50']}",
        f"  hours_to_stop={result['hours_to_stop']}",
        "",
    ]
    for r in (0.5, 0.75, 1.0, 2.0):
        lines.append(f"  R={r}")
        for hz in ("24", "48", "72", "any"):
            lines.append(f"    {hz:>3}  {cell(all_g, r, hz)}")
    lines += ["", "  B3/S3 0.5R@24 与 1R@any："]
    lines.append(f"    B3 0.5@24 {cell(b3_g, 0.5, '24')}  1@any {cell(b3_g, 1.0, 'any')}")
    lines.append(f"    S3 0.5@24 {cell(s3_g, 0.5, '24')}  1@any {cell(s3_g, 1.0, 'any')}")
    lines += ["", result["blocked"]]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
