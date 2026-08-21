"""CHAN_B3_BASELINE_V1. Frozen B3/S3. 1R. 24h. No EMA/OF/ATR."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_b3_baseline.paths import (
    ACCOUNT,
    E3_MOTHER,
    EXPECTED_N_15M,
    EXPECTED_N_B3,
    EXPECTED_N_EVENT,
    EXPECTED_N_S3,
    KLINE_1M,
    LOG,
    RISK_FRAC,
    TIME_BARS,
)
from chan_b3_baseline.simulate import simulate_one
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


def _slice(rows: list[dict], pred) -> dict:
    sub = [r for r in rows if pred(r)]
    traded = [r for r in sub if r["r_mult"] is not None]
    rs = [r["r_mult"] for r in traded]
    wins = [r for r in traded if r["outcome"] == "WIN"]
    losses = [r for r in traded if r["outcome"] == "LOSS"]
    times = [r for r in traded if r["outcome"] == "TIME_EXIT"]
    n_w, n_l, n_t = len(wins), len(losses), len(times)
    resolved = n_w + n_l
    gross_w = sum(r["r_mult"] for r in wins)
    gross_l = abs(sum(r["r_mult"] for r in losses))
    return {
        "n": len(sub),
        "traded": len(traded),
        "outcome": dict(Counter(r["outcome"] for r in sub)),
        "win": n_w,
        "loss": n_l,
        "time_exit": n_t,
        "win_rate_resolved": round(n_w / resolved, 6) if resolved else None,
        "avg_r": round(sum(rs) / len(rs), 6) if rs else None,
        "median_r": None if not rs else sorted(rs)[len(rs) // 2],
        "total_r": round(sum(rs), 6) if rs else None,
        "total_usdt": round(sum(r["pnl_usdt"] for r in traded), 4),
        "pf": round(gross_w / gross_l, 6) if gross_l else None,
        "mfe_r": _q([r["mfe_r"] for r in traded]),
        "mae_r": _q([r["mae_r"] for r in traded]),
        "mfe_24h_r": _q([r["mfe_24h_r"] for r in traded]),
        "mae_24h_r": _q([r["mae_24h_r"] for r in traded]),
        "hours_to_tp": _q([r["hours_to_exit"] for r in wins]),
        "hours_to_stop": _q([r["hours_to_exit"] for r in losses]),
        "hours_to_time": _q([r["hours_to_exit"] for r in times]),
        "same_bar_both": sum(1 for r in sub if r.get("same_bar_both")),
        "r_px": _q([r["r_px"] for r in traded if r.get("r_px") is not None]),
    }


def _hint(all_s: dict, b3: dict, s3: dict) -> str:
    """Descriptive only. Not a next-shot authorization."""
    mfe24 = all_s["mfe_24h_r"]
    med_mfe24 = None if not mfe24 else mfe24["p50"]
    n = all_s["n"]
    if n and all_s["time_exit"] >= n / 2 and (med_mfe24 is None or med_mfe24 < 1.0):
        return "TIME_DOMINATED"
    if med_mfe24 is not None and med_mfe24 >= 2.0:
        return "A_TARGET"
    if all_s["loss"] > all_s["win"] and all_s["loss"] >= n / 3:
        return "B_STOP"
    b3_r, s3_r = b3["avg_r"], s3["avg_r"]
    if b3_r is not None and s3_r is not None and abs(b3_r - s3_r) >= 0.5:
        return "E_SIDE"
    return "WATCH"


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    events = load_events(E3_MOTHER)
    rows = [simulate_one(ev, bar, ACCOUNT) for ev in events]
    n_b3 = sum(1 for r in rows if r["kind"] == "B3")
    n_s3 = sum(1 for r in rows if r["kind"] == "S3")
    if len(bar) != EXPECTED_N_15M or len(rows) != EXPECTED_N_EVENT or n_b3 != EXPECTED_N_B3 or n_s3 != EXPECTED_N_S3:
        decision, kind = "FAIL", "CLOCK"
    else:
        decision, kind = "PASS", "BASELINE_OK"

    all_s = _slice(rows, lambda r: True)
    b3 = _slice(rows, lambda r: r["kind"] == "B3")
    s3 = _slice(rows, lambda r: r["kind"] == "S3")
    long_s = _slice(rows, lambda r: r["side"] == "LONG")
    short_s = _slice(rows, lambda r: r["side"] == "SHORT")
    hint = _hint(all_s, b3, s3)
    result = {
        "decision": decision,
        "kind": kind,
        "hint": hint,
        "n_event": len(rows),
        "n_b3": n_b3,
        "n_s3": n_s3,
        "account": ACCOUNT,
        "risk_frac": RISK_FRAC,
        "time_bars": TIME_BARS,
        "all": all_s,
        "B3": b3,
        "S3": s3,
        "LONG": long_s,
        "SHORT": short_s,
        "blocked": (
            "无 EMA/OF/Trend Age/ATR。无手续费。非组合。"
            "BASELINE_OK ≠ Edge ≠ 实盘。"
            "不准本枪优化 TP/Stop。"
            f"hint={hint} 只是观察标签，不是下一枪授权。"
        ),
    }
    (LOG / "BASELINE.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "TRADES.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def line(name: str, d: dict) -> str:
        return (
            f"  {name} n={d['n']} WIN={d['win']} LOSS={d['loss']} TIME={d['time_exit']} "
            f"wr={d['win_rate_resolved']} avgR={d['avg_r']} medR={d['median_r']} "
            f"sumR={d['total_r']} PF={d['pf']} "
            f"mfe_p50={None if not d['mfe_r'] else d['mfe_r']['p50']} "
            f"mae_p50={None if not d['mae_r'] else d['mae_r']['p50']} "
            f"mfe24_p50={None if not d['mfe_24h_r'] else d['mfe_24h_r']['p50']}"
        )

    lines = [
        f"CHAN_B3_BASELINE_V1  decision={decision}  kind={kind}  hint={hint}",
        "15m B3/S3 · T1 open · Stop=盒沿 · TP=1R · 24h TIME_EXIT · risk=0.5% · 无费",
        "",
        line("ALL", all_s),
        line("B3 ", b3),
        line("S3 ", s3),
        "",
        f"  hours_to_tp={all_s['hours_to_tp']}  hours_to_stop={all_s['hours_to_stop']}",
        f"  same_bar_both={all_s['same_bar_both']}  r_px={all_s['r_px']}",
        "",
        result["blocked"],
    ]
    out = LOG / "BASELINE.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
