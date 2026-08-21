"""CHAN_S3_HIST_001. Frozen B3/S3 definition on pre-tape history. Not OOS."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

ROOT = __import__("pathlib").Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_b3_v2.simulate import simulate_one
from chan_fractal_of.clock import resample_bars
from chan_s3_hist.paths import (
    ACCOUNT,
    CENSUS_END,
    CENSUS_START,
    DATA_START,
    HIT24_RANDOM,
    KLINE_1M,
    LOG,
    MIN_N,
    PERM_ALPHA,
    PERM_N,
    PERM_NULL,
    PERM_SEED,
    TP_MULT,
    YEAR_MIN_N,
)
from chan_3rd_point.scan import scan_third


def _ts(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert("UTC")


def _q(xs: list[float]) -> dict | None:
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)

    def at(p: float) -> float:
        return round(s[min(n - 1, int(p * (n - 1)))], 6)

    return {"n": n, "min": round(s[0], 6), "p25": at(0.25), "p50": at(0.5), "p75": at(0.75), "max": round(s[-1], 6)}


def _slice(rows: list[dict]) -> dict:
    traded = [r for r in rows if r.get("r_mult") is not None]
    rs = [r["r_mult"] for r in traded]
    wins = [r for r in traded if r["outcome"] == "WIN"]
    losses = [r for r in traded if r["outcome"] == "LOSS"]
    times = [r for r in traded if r["outcome"] == "TIME_EXIT"]
    n = len(rows)
    n_t = len(traded)
    return {
        "n": n,
        "traded": n_t,
        "outcome": dict(Counter(r["outcome"] for r in rows)),
        "win": len(wins),
        "loss": len(losses),
        "time_exit": len(times),
        "time_share": round(len(times) / n_t, 6) if n_t else None,
        "hit24": round(len(wins) / n_t, 6) if n_t else None,
        "avg_r": round(sum(rs) / len(rs), 6) if rs else None,
        "median_r": None if not rs else round(sorted(rs)[len(rs) // 2], 6),
        "total_r": round(sum(rs), 6) if rs else None,
        "se_r": round(float(np.std(rs, ddof=1) / math.sqrt(len(rs))), 6) if len(rs) > 1 else None,
    }


def _perm_p(rs: list[float], n: int, seed: int) -> float | None:
    if len(rs) < 2:
        return None
    obs = float(np.mean(rs))
    rng = np.random.default_rng(seed)
    arr = np.asarray(rs, dtype=float)
    hits = 0
    for _ in range(n):
        signs = rng.choice(np.array([-1.0, 1.0]), size=len(arr))
        if float(np.mean(arr * signs)) >= obs:
            hits += 1
    return round((hits + 1) / (n + 1), 6)


def _gaps_hours(events: list[dict]) -> list[float]:
    ts = sorted(_ts(e["T_3_VISIBLE"]) for e in events)
    return [round((b - a).total_seconds() / 3600.0, 4) for a, b in zip(ts, ts[1:])]


def _year_table(rows: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        ts = r.get("entry_ts") or r.get("T_3_VISIBLE")
        buckets[str(_ts(ts).year)].append(r)
    return {y: _slice(v) for y, v in sorted(buckets.items())}


def _verdict(s3: dict, years: dict, perm_p: float | None) -> tuple[str, str]:
    n = s3["traded"] or 0
    avg = s3["avg_r"]
    hit = s3["hit24"]
    if n < MIN_N or avg is None or hit is None or perm_p is None:
        return "INCONCLUSIVE", "THIN"
    thick = {y: d for y, d in years.items() if (d["traded"] or 0) >= YEAR_MIN_N and d["avg_r"] is not None}
    year_ok = True
    if thick:
        year_ok = sum(1 for d in thick.values() if d["avg_r"] > 0) >= math.ceil(len(thick) / 2)
    if avg > 0 and perm_p <= PERM_ALPHA and year_ok:
        return "WORTH_WAIT", "S3_EDGE"
    if avg <= 0 and perm_p > PERM_NULL and hit < HIT24_RANDOM:
        return "NOT_WORTH_WAIT", "S3_NULL"
    return "INCONCLUSIVE", "MIXED"


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    t0 = _ts(CENSUS_START)
    t1 = _ts(CENSUS_END)
    raw = pd.read_parquet(KLINE_1M)
    raw["open_ts"] = pd.to_datetime(raw["open_ts"], utc=True)
    data0 = _ts(DATA_START)
    raw = raw[(raw["open_ts"] >= data0) & (raw["open_ts"] < t1)].copy()
    bar = resample_bars(raw, 15)
    payload = scan_third(bar)
    kept = []
    for ev in payload["events"]:
        t3 = _ts(ev["T_3_VISIBLE"])
        if t0 <= t3 < t1:
            kept.append(ev)
    rows = [simulate_one(ev, bar, ACCOUNT, TP_MULT) for ev in kept]
    # attach clocks used for year / drought
    by_id = {e["event_id"]: e for e in kept}
    for r in rows:
        src = by_id[r["event_id"]]
        r["T_3_VISIBLE"] = src["T_3_VISIBLE"]
        r["t0_close_ts"] = r.get("entry_ts")

    b3_ev = [e for e in kept if e["kind"] == "B3"]
    s3_ev = [e for e in kept if e["kind"] == "S3"]
    b3 = _slice([r for r in rows if r["kind"] == "B3"])
    s3 = _slice([r for r in rows if r["kind"] == "S3"])
    s3_traded = [r for r in rows if r["kind"] == "S3" and r.get("r_mult") is not None]
    perm = _perm_p([r["r_mult"] for r in s3_traded], PERM_N, PERM_SEED)
    years_s3 = _year_table([r for r in rows if r["kind"] == "S3"])
    years_b3 = _year_table([r for r in rows if r["kind"] == "B3"])
    decision, kind = _verdict(s3, years_s3, perm)
    days = (t1 - t0).total_seconds() / 86400.0
    s3_per_90 = round(len(s3_ev) / days * 90.0, 4) if days else None
    gaps = _gaps_hours(s3_ev)
    result = {
        "decision": decision,
        "kind": kind,
        "not_oos": True,
        "g0_unchanged": True,
        "n_15m": int(len(bar)),
        "n_event": len(kept),
        "n_b3": len(b3_ev),
        "n_s3": len(s3_ev),
        "days": round(days, 2),
        "s3_per_90d": s3_per_90,
        "tp_mult": TP_MULT,
        "census_start": CENSUS_START,
        "census_end": CENSUS_END,
        "all": _slice(rows),
        "B3": b3,
        "S3": s3,
        "S3_perm_p_mean_gt_0": perm,
        "S3_by_year": years_s3,
        "B3_by_year": years_b3,
        "S3_gap_hours": _q(gaps),
        "blocked": (
            "不是 OOS。不改 S3 定义。不取消 G0。不准偷看 9…15。"
            "0.5R 选在 90 天窗，本枪只诊断更早历史。"
            "WORTH_WAIT / NOT_WORTH_WAIT 都不替代 Recheck。"
        ),
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text("\n".join(json.dumps(r, default=str) for r in rows) + "\n")
    lines = [
        f"CHAN_S3_HIST_001  decision={decision}  kind={kind}  not_oos=True",
        f"事件窗 {CENSUS_START} ≤ T_3 < {CENSUS_END}。G0 8→16 不动。",
        "",
        f"  n_15m={len(bar)} days={result['days']} n_b3={len(b3_ev)} n_s3={len(s3_ev)} s3_per_90d={s3_per_90}",
        f"  S3 traded={s3['traded']} WIN={s3['win']} LOSS={s3['loss']} TIME={s3['time_exit']} "
        f"hit24={s3['hit24']} avgR={s3['avg_r']} seR={s3['se_r']} perm_p={perm}",
        f"  B3 traded={b3['traded']} WIN={b3['win']} LOSS={b3['loss']} TIME={b3['time_exit']} "
        f"hit24={b3['hit24']} avgR={b3['avg_r']}",
        f"  S3 gap_h p50={None if not result['S3_gap_hours'] else result['S3_gap_hours']['p50']} "
        f"max={None if not result['S3_gap_hours'] else result['S3_gap_hours']['max']}",
        "",
        "  S3 by year:",
    ]
    for y, d in years_s3.items():
        lines.append(
            f"    {y} n={d['traded']} hit24={d['hit24']} avgR={d['avg_r']} "
            f"WIN/LOSS/TIME={d['win']}/{d['loss']}/{d['time_exit']}"
        )
    lines += ["", result["blocked"]]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
