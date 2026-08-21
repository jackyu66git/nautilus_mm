"""Trend × EMA bucket contrast. No OF. No WHERE_001 rewrite."""
from __future__ import annotations

from collections import Counter

FATES = ("RESUME", "NEW_ZS", "RANGE_REENTRY", "REVERSE", "CENSOR")


def _rate(rows: list[dict], fate: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for r in rows if r["fate"] == fate) / len(rows), 6)


def _p50(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2]


def audit(states: list[str], episodes: list[dict], n_1h: int) -> dict:
    bar_n = Counter(states)
    clock_ok = True
    for r in episodes:
        if r["state_at_swing"] not in ("TREND_UP", "TREND_DOWN"):
            clock_ok = False
        if r.get("T_CHECKPOINT") and not (r["T_SWING_VISIBLE"] < r["T_CHECKPOINT"] <= r["T_END"]):
            clock_ok = False
    ck = [r for r in episodes if r.get("bucket") in ("NEAR", "FAR", "MID", "CROSS")]
    near = [r for r in ck if r["bucket"] == "NEAR"]
    far = [r for r in ck if r["bucket"] == "FAR"]
    mid = [r for r in ck if r["bucket"] == "MID"]
    cross = [r for r in ck if r["bucket"] == "CROSS"]
    thin = min(len(near), len(far)) < 10
    resume_n = _rate(near, "RESUME")
    resume_f = _rate(far, "RESUME")
    if not clock_ok:
        decision, kind = "FAIL", "LEAK"
    elif bar_n["RANGE"] == 0 or (bar_n["TREND_UP"] + bar_n["TREND_DOWN"] == 0):
        decision, kind = "FAIL", "NO_OBJECT"
    elif not episodes:
        decision, kind = "FAIL", "NO_TREND_PULLBACK"
    elif thin:
        decision, kind = "PASS", "SAMPLE_INSUFFICIENT"
    else:
        delta = abs((resume_n or 0) - (resume_f or 0))
        if delta < 0.15:
            decision, kind = "FAIL", "NO_STATE_CONTRAST"
        else:
            decision, kind = "PASS", "HAS_CONTRAST"
    return {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "n_1h": n_1h,
        "n_range": bar_n["RANGE"],
        "n_transition": bar_n["TRANSITION"],
        "n_trend_up": bar_n["TREND_UP"],
        "n_trend_down": bar_n["TREND_DOWN"],
        "n_none": bar_n["NONE"],
        "n_episode": len(episodes),
        "n_checkpoint": len(ck),
        "n_near": len(near),
        "n_mid": len(mid),
        "n_far": len(far),
        "n_cross": len(cross),
        "near_resume": resume_n,
        "far_resume": resume_f,
        "near_reentry": _rate(near, "RANGE_REENTRY"),
        "far_reentry": _rate(far, "RANGE_REENTRY"),
        "near_hours_p50": _p50([r["hours_to_end"] for r in near]),
        "far_hours_p50": _p50([r["hours_to_end"] for r in far]),
        "fate_all": dict(Counter(r["fate"] for r in episodes)),
        "blocked": "无 OF/MACD/三买/阈值搜索。RANGE 不进对照。WHERE_001 数字不可变。",
    }
