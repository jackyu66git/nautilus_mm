"""CHAN_B3_V2. TP 0.5 / 0.75 / 1.0. Same Entry/Stop/Time. No fees."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_b3_v2.paths import (
    ACCOUNT,
    AVG_IMPROVE,
    E3_MOTHER,
    EXPECTED_N_15M,
    EXPECTED_N_B3,
    EXPECTED_N_EVENT,
    EXPECTED_N_S3,
    FAMILY_CONFLICT,
    KLINE_1M,
    LOG,
    TIME_DROP,
    TP_VARIANTS,
    V1_AVG_R,
    V1_LOSS,
    V1_TIME,
    V1_TIME_SHARE,
    V1_WIN,
)
from chan_b3_v2.simulate import simulate_one
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


def _slice(rows: list[dict]) -> dict:
    traded = [r for r in rows if r["r_mult"] is not None]
    rs = [r["r_mult"] for r in traded]
    wins = [r for r in traded if r["outcome"] == "WIN"]
    losses = [r for r in traded if r["outcome"] == "LOSS"]
    times = [r for r in traded if r["outcome"] == "TIME_EXIT"]
    n_w, n_l, n_t = len(wins), len(losses), len(times)
    resolved = n_w + n_l
    n = len(rows)
    gross_w = sum(r["r_mult"] for r in wins)
    gross_l = abs(sum(r["r_mult"] for r in losses))
    return {
        "n": n,
        "traded": len(traded),
        "outcome": dict(Counter(r["outcome"] for r in rows)),
        "win": n_w,
        "loss": n_l,
        "time_exit": n_t,
        "time_share": round(n_t / n, 6) if n else None,
        "target_hit": round(n_w / n, 6) if n else None,
        "stop_share": round(n_l / n, 6) if n else None,
        "win_rate_resolved": round(n_w / resolved, 6) if resolved else None,
        "avg_r": round(sum(rs) / len(rs), 6) if rs else None,
        "median_r": None if not rs else round(sorted(rs)[len(rs) // 2], 6),
        "total_r": round(sum(rs), 6) if rs else None,
        "total_usdt": round(sum(r["pnl_usdt"] for r in traded), 4),
        "pf": round(gross_w / gross_l, 6) if gross_l else None,
        "hours_to_tp": _q([r["hours_to_exit"] for r in wins]),
        "hours_to_stop": _q([r["hours_to_exit"] for r in losses]),
    }


def _expectancy_ok(avg_r: float | None) -> bool:
    if avg_r is None:
        return False
    return avg_r > 0 or avg_r >= V1_AVG_R + AVG_IMPROVE


def _conflict(b3: dict, s3: dict) -> bool:
    a, b = b3["avg_r"], s3["avg_r"]
    if a is None or b is None:
        return False
    return (a >= FAMILY_CONFLICT and b <= -FAMILY_CONFLICT) or (
        b >= FAMILY_CONFLICT and a <= -FAMILY_CONFLICT
    )


def _loo_ok(rows: list[dict]) -> bool:
    traded = [r for r in rows if r["r_mult"] is not None]
    if len(traded) < 2:
        return False
    worst = max(traded, key=lambda r: abs(r["r_mult"]))
    rest = [r["r_mult"] for r in traded if r["event_id"] != worst["event_id"]]
    avg = sum(rest) / len(rest)
    return _expectancy_ok(avg)


def _gate(name: str, all_s: dict, b3: dict, s3: dict, rows: list[dict]) -> dict:
    time_ok = all_s["time_share"] is not None and all_s["time_share"] <= V1_TIME_SHARE - TIME_DROP
    exp_ok = _expectancy_ok(all_s["avg_r"])
    conf = _conflict(b3, s3)
    loo = _loo_ok(rows)
    passed = bool(time_ok and exp_ok and (not conf) and loo)
    return {
        "variant": name,
        "time_ok": time_ok,
        "expectancy_ok": exp_ok,
        "no_conflict": not conf,
        "loo_ok": loo,
        "pass": passed,
    }


def _line(name: str, d: dict) -> str:
    return (
        f"  {name} n={d['n']} WIN={d['win']} LOSS={d['loss']} TIME={d['time_exit']} "
        f"time%={d['time_share']} hit={d['target_hit']} stop%={d['stop_share']} "
        f"avgR={d['avg_r']} medR={d['median_r']} sumR={d['total_r']} PF={d['pf']}"
    )


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    events = load_events(E3_MOTHER)
    variants = {}
    trades_out = []
    for name, tp in TP_VARIANTS:
        rows = [simulate_one(ev, bar, ACCOUNT, tp) for ev in events]
        for r in rows:
            r["variant"] = name
            trades_out.append(r)
        all_s = _slice(rows)
        b3 = _slice([r for r in rows if r["kind"] == "B3"])
        s3 = _slice([r for r in rows if r["kind"] == "S3"])
        variants[name] = {
            "tp_mult": tp,
            "all": all_s,
            "B3": b3,
            "S3": s3,
            "gate": _gate(name, all_s, b3, s3, rows),
        }

    v100 = variants["V2_100"]["all"]
    clock = (
        len(bar) == EXPECTED_N_15M
        and len(events) == EXPECTED_N_EVENT
        and v100["win"] == V1_WIN
        and v100["loss"] == V1_LOSS
        and v100["time_exit"] == V1_TIME
        and sum(1 for e in events if e["kind"] == "B3") == EXPECTED_N_B3
        and sum(1 for e in events if e["kind"] == "S3") == EXPECTED_N_S3
    )
    passed = [k for k, v in variants.items() if v["gate"]["pass"]]
    v050 = variants["V2_050"]["all"]
    fail_050 = (not variants["V2_050"]["gate"]["pass"]) and (v050["avg_r"] is not None and v050["avg_r"] <= 0) and (
        v050["target_hit"] is not None and v050["target_hit"] >= 0.40
    )
    if not clock:
        decision, kind = "FAIL", "CLOCK"
        freeze = None
    elif passed:
        freeze = min(passed, key=lambda k: variants[k]["tp_mult"])
        decision, kind = "PASS", freeze
    elif fail_050:
        decision, kind = "FAIL", "NO_TP_EDGE"
        freeze = None
    elif variants["V2_050"]["gate"]["time_ok"] and variants["V2_050"]["gate"]["expectancy_ok"] and not variants["V2_050"]["gate"]["no_conflict"]:
        decision, kind = "HOLD", "FAMILY_SPLIT"
        freeze = None
    else:
        decision, kind = "HOLD", "NO_PASS"
        freeze = None

    result = {
        "decision": decision,
        "kind": kind,
        "freeze": freeze,
        "n_event": len(events),
        "variants": variants,
        "passed": passed,
        "blocked": (
            "无 EMA/OF/ATR。无手续费。B3/S3 分记。不按 PF 选参。"
            "PASS 冻结最小通过 TP。OOS 另授权。同一 20 笔 ≠ OOS。"
            "FAIL/NO_TP_EDGE → 停 TP 线，才看 Entry。不准加指标。"
        ),
    }
    (LOG / "V2.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "TRADES.jsonl").write_text("\n".join(json.dumps(r) for r in trades_out) + "\n")
    lines = [
        f"CHAN_B3_V2  decision={decision}  kind={kind}  freeze={freeze}",
        "唯一变量 TP。Entry/Stop/24h 冻结。无费。",
        "",
    ]
    for name, tp in TP_VARIANTS:
        v = variants[name]
        g = v["gate"]
        lines.append(_line(f"{name} tp={tp}", v["all"]))
        lines.append(_line("     B3", v["B3"]))
        lines.append(_line("     S3", v["S3"]))
        lines.append(
            f"     gate time_ok={g['time_ok']} exp_ok={g['expectancy_ok']} "
            f"no_conflict={g['no_conflict']} loo_ok={g['loo_ok']} pass={g['pass']}"
        )
        lines.append("")
    lines.append(result["blocked"])
    out = LOG / "V2.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
