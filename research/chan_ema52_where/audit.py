"""Census + NEAR/FAR contrast. No MACD, no 3rd point, no P&L."""
from __future__ import annotations


def _rate(rows: list[dict], fate: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for r in rows if r["fate"] == fate) / len(rows), 6)


def audit(episodes: list[dict], n_1h: int) -> dict:
    clock_ok = True
    for r in episodes:
        if r.get("T_NEAR_VISIBLE"):
            if not (r["T_SWING_VISIBLE"] < r["T_NEAR_VISIBLE"] <= r["T_END"]):
                clock_ok = False
        elif not (r["T_SWING_VISIBLE"] <= r["T_END"]):
            clock_ok = False
    n = len(episodes)
    near = [r for r in episodes if r["near"]]
    far_end = [r for r in episodes if not r["near"]]
    ck_near = [r for r in episodes if r.get("checkpoint") == "NEAR"]
    ck_far = [r for r in episodes if r.get("checkpoint") == "FAR"]
    resume_n = _rate(near, "RESUME")
    break_n = _rate(near, "BREAK")
    resume_ck_n = _rate(ck_near, "RESUME")
    resume_ck_f = _rate(ck_far, "RESUME")
    thin = min(len(ck_near), len(ck_far)) < 10
    if not clock_ok:
        decision, kind = "FAIL", "LEAK"
    elif n == 0:
        decision, kind = "FAIL", "NO_OBJECT"
    elif not near:
        decision, kind = "FAIL", "NO_TOUCH"
    elif thin:
        decision, kind = "PASS", "CENSUS_OK"
        contrast = "SAMPLE_INSUFFICIENT"
    else:
        contrast = "NO_STATE_CONTRAST"
        if resume_ck_n is not None and resume_ck_f is not None:
            if abs(resume_ck_n - resume_ck_f) >= 0.15:
                contrast = "HAS_CONTRAST"
        decision = "FAIL" if contrast == "NO_STATE_CONTRAST" else "PASS"
        kind = contrast if contrast != "HAS_CONTRAST" else "CENSUS_OK"
        if contrast == "HAS_CONTRAST":
            kind = "HAS_CONTRAST"
    return {
        "decision": decision,
        "kind": kind,
        "clock_ok": clock_ok,
        "n_1h": n_1h,
        "n_episode": n,
        "n_up": sum(1 for r in episodes if r["side"] == "UP"),
        "n_down": sum(1 for r in episodes if r["side"] == "DOWN"),
        "n_near": len(near),
        "n_never_near": len(far_end),
        "n_resume": sum(1 for r in episodes if r["fate"] == "RESUME"),
        "n_break": sum(1 for r in episodes if r["fate"] == "BREAK"),
        "n_censor": sum(1 for r in episodes if r["fate"] == "CENSOR"),
        "near_resume_rate": resume_n,
        "near_break_rate": break_n,
        "n_checkpoint_near": len(ck_near),
        "n_checkpoint_far": len(ck_far),
        "checkpoint_near_resume_rate": resume_ck_n,
        "checkpoint_far_resume_rate": resume_ck_f,
        "contrast": kind if decision != "FAIL" or kind == "NO_STATE_CONTRAST" else "NA",
        "blocked": "无 MACD / 三买 / OF / SMC / 收益。不准用均线定义三买。",
    }
