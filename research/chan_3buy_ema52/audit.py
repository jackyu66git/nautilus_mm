"""3rd-point × EMA52 entered vs not. Structural fate only."""
from __future__ import annotations

from collections import Counter


def _rate(rows: list[dict], fate: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for r in rows if r["fate"] == fate) / len(rows), 6)


def audit(rows: list[dict], n_mother: int) -> dict:
    clock_ok = True
    for r in rows:
        if r["fate"] == "NO_PULLBACK":
            continue
        if not (r["T_3_VISIBLE"] < r["T_PB_VISIBLE"] <= r["T_END"]):
            clock_ok = False
    usable = [r for r in rows if r["entered"] is not None]
    entered = [r for r in usable if r["entered"]]
    missed = [r for r in usable if not r["entered"]]
    thin = min(len(entered), len(missed)) < 10
    re_in = _rate(entered, "RESUME")
    re_out = _rate(missed, "RESUME")
    if not clock_ok:
        decision, kind = "FAIL", "LEAK"
    elif n_mother != 20:
        decision, kind = "FAIL", "CLOCK"
    elif not usable:
        decision, kind = "FAIL", "NO_PULLBACK"
    elif thin:
        decision, kind = "PASS", "SAMPLE_INSUFFICIENT"
    else:
        delta = abs((re_in or 0) - (re_out or 0))
        if delta < 0.15:
            decision, kind = "FAIL", "NO_FATE_CONTRAST"
        else:
            decision, kind = "PASS", "HAS_CONTRAST"
    return {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "n_mother": n_mother,
        "n_b3": sum(1 for r in rows if r["kind"] == "B3"),
        "n_s3": sum(1 for r in rows if r["kind"] == "S3"),
        "n_no_pb": sum(1 for r in rows if r["fate"] == "NO_PULLBACK"),
        "n_usable": len(usable),
        "n_entered": len(entered),
        "n_not_entered": len(missed),
        "entered_resume": re_in,
        "missed_resume": re_out,
        "entered_reentry": _rate(entered, "REENTRY"),
        "missed_reentry": _rate(missed, "REENTRY"),
        "fate_all": dict(Counter(r["fate"] for r in rows)),
        "blocked": "无 OF/MACD/EMA 搜索/30m/1H 等效尺度。不准改三买定义。",
    }
