"""CHAN_B3_R_CENSUS_001. Raw R distribution. No strategy change."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))

from chan_b3_r_census.paths import (
    EXPECTED_N_B3,
    EXPECTED_N_EVENT,
    EXPECTED_N_S3,
    LOG,
    RATIO_MAX,
    RATIO_P90,
    RATIO_P95,
    V1_TRADES,
)


def _load_trades(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _q(xs: list[float]) -> dict | None:
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)

    def at(p: float) -> float:
        return round(s[min(n - 1, int(p * (n - 1)))], 6)

    return {
        "n": n,
        "min": round(s[0], 6),
        "p25": at(0.25),
        "p50": at(0.50),
        "p75": at(0.75),
        "p90": at(0.90),
        "p95": at(0.95),
        "max": round(s[-1], 6),
    }


def _enrich(row: dict) -> dict:
    entry = float(row["entry"])
    stop = float(row["stop"])
    r_px = float(row["r_px"])
    r_pct = r_px / entry
    return {
        "event_id": row["event_id"],
        "kind": row["kind"],
        "side": row["side"],
        "entry": entry,
        "stop": stop,
        "zg": row.get("zg"),
        "zd": row.get("zd"),
        "r_px": r_px,
        "r_pct": round(r_pct, 8),
        "tp_0.5_px": round(0.5 * r_px, 4),
        "tp_0.5_pct": round(0.5 * r_pct, 8),
        "outcome": row["outcome"],
        "hours_to_exit": row.get("hours_to_exit"),
        "mfe_r": row.get("mfe_r"),
        "mfe_24h_r": row.get("mfe_24h_r"),
        "mae_r": row.get("mae_r"),
    }


def _ratios(q: dict | None) -> dict | None:
    if not q or not q["p50"]:
        return None
    p50 = q["p50"]
    return {
        "p90_over_p50": round(q["p90"] / p50, 4),
        "p95_over_p50": round(q["p95"] / p50, 4),
        "max_over_p50": round(q["max"] / p50, 4),
    }


def _verdict(ratios: dict | None) -> tuple[str, list[str]]:
    if not ratios:
        return "FAIL", ["NO_RATIOS"]
    hits = []
    if ratios["p90_over_p50"] >= RATIO_P90:
        hits.append("P90")
    if ratios["p95_over_p50"] >= RATIO_P95:
        hits.append("P95")
    if ratios["max_over_p50"] >= RATIO_MAX:
        hits.append("MAX")
    return ("LONG_TAIL" if hits else "NO_TAIL"), hits


def _slice_q(rows: list[dict], key: str) -> dict | None:
    return _q([r[key] for r in rows])


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    raw = _load_trades(V1_TRADES)
    rows = [_enrich(r) for r in raw]
    n_b3 = sum(1 for r in rows if r["kind"] == "B3")
    n_s3 = sum(1 for r in rows if r["kind"] == "S3")
    clock = (
        len(rows) == EXPECTED_N_EVENT
        and n_b3 == EXPECTED_N_B3
        and n_s3 == EXPECTED_N_S3
        and all(r["r_px"] > 0 for r in rows)
    )
    all_q = _slice_q(rows, "r_pct")
    b3_q = _slice_q([r for r in rows if r["kind"] == "B3"], "r_pct")
    s3_q = _slice_q([r for r in rows if r["kind"] == "S3"], "r_pct")
    ratios = _ratios(all_q)
    if not clock:
        decision, kind = "FAIL", "CLOCK"
        hits = ["CLOCK"]
        next_gate = "STOP"
    else:
        decision, hits = _verdict(ratios)
        kind = "+".join(hits) if hits else "SHAPE_OK"
        next_gate = "G0b" if decision == "LONG_TAIL" else "G0_WAIT"

    p90 = None if not all_q else all_q["p90"]
    result = {
        "decision": decision,
        "kind": kind,
        "next_gate": next_gate,
        "n_event": len(rows),
        "n_b3": n_b3,
        "n_s3": n_s3,
        "clock_ok": clock,
        "r_pct": {"all": all_q, "B3": b3_q, "S3": s3_q},
        "r_px": {
            "all": _slice_q(rows, "r_px"),
            "B3": _slice_q([r for r in rows if r["kind"] == "B3"], "r_px"),
            "S3": _slice_q([r for r in rows if r["kind"] == "S3"], "r_px"),
        },
        "tp_0.5_pct": _slice_q(rows, "tp_0.5_pct"),
        "ratios": ratios,
        "thresholds": {"p90_over_p50": RATIO_P90, "p95_over_p50": RATIO_P95, "max_over_p50": RATIO_MAX},
        "hits": hits,
        "g0b_p90": p90 if decision == "LONG_TAIL" else None,
        "outcome": dict(Counter(r["outcome"] for r in rows)),
        "by_outcome_r_pct": {
            k: _q([r["r_pct"] for r in rows if r["outcome"] == k])
            for k in ("WIN", "LOSS", "TIME_EXIT")
        },
        "blocked": (
            "不改 Entry/Stop/TP/Time。不要 Cap Stop。不定 5/10/15%。"
            "NO_TAIL → G0 WAIT。LONG_TAIL → G0b SKIP if R_pct>p90。"
            "不准只做 B3。不跑 Recheck。"
        ),
    }
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def fmt(q: dict | None) -> str:
        if not q:
            return "none"
        return (
            f"p25={q['p25']:.4%} p50={q['p50']:.4%} p75={q['p75']:.4%} "
            f"p90={q['p90']:.4%} p95={q['p95']:.4%} max={q['max']:.4%}"
        )

    ranked = sorted(rows, key=lambda r: r["r_pct"], reverse=True)
    lines = [
        f"CHAN_B3_R_CENSUS_001  decision={decision}  kind={kind}  next={next_gate}",
        "Raw R = |Entry-Stop|/Entry。不改 Stop。不定 5/10/15%。",
        "",
        f"  all  {fmt(all_q)}",
        f"  B3   {fmt(b3_q)}",
        f"  S3   {fmt(s3_q)}",
        f"  ratios p90/p50={None if not ratios else ratios['p90_over_p50']} "
        f"p95/p50={None if not ratios else ratios['p95_over_p50']} "
        f"max/p50={None if not ratios else ratios['max_over_p50']}",
        f"  gate LONG_TAIL if p90/p50>={RATIO_P90} or p95/p50>={RATIO_P95} or max/p50>={RATIO_MAX}",
        "",
        "  R_pct vs outcome / MFE / TIME（按 R_pct 降序）",
    ]
    for r in ranked:
        lines.append(
            f"    {r['kind']} {r['r_pct']:.4%} r_px={r['r_px']:.1f} "
            f"tp0.5={r['tp_0.5_pct']:.4%} {r['outcome']} "
            f"h={r['hours_to_exit']} mfeR={r['mfe_r']}  {r['event_id']}"
        )
    lines += ["", result["blocked"]]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
