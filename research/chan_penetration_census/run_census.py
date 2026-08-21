"""CHAN_PENETRATION_CENSUS_001. Reverse excursion / anchor pierce. No ATR. No PnL."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_cont_null.scan import load_events
from chan_fractal_of.clock import resample_bars
from chan_penetration_census.paths import (
    BLOB_MAX,
    BUCKET_MIN,
    CONT,
    EXPECTED_N_15M,
    EXPECTED_N_B1,
    EXPECTED_N_B2,
    EXPECTED_N_B3,
    EXPECTED_N_EVENT,
    KLINE_1M,
    LOG,
)
from chan_penetration_census.scan import follow_penetration, scan_anchors

B12_LAYERS = ("NONE", "SHALLOW", "PRIMARY")
B3_LAYERS = ("NONE", "SHALLOW", "BOX", "THROUGH")


def _q(xs: list[float]) -> dict | None:
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)

    def at(p: float) -> float:
        return round(s[min(n - 1, int(p * (n - 1)))], 4)

    return {"n": n, "min": round(s[0], 4), "p25": at(0.25), "p50": at(0.5), "p75": at(0.75), "max": round(s[-1], 4)}


def _layers(rows: list[dict], order: tuple[str, ...]) -> dict:
    c = Counter(r["layer"] for r in rows)
    n = len(rows)
    counts = {k: int(c.get(k, 0)) for k in order}
    nonempty = [k for k, v in counts.items() if v >= BUCKET_MIN]
    top = (max(counts.values()) / n) if n else 1.0
    return {
        "n": n,
        "counts": counts,
        "visible": nonempty,
        "top_share": round(top, 4),
        "has_layers": n >= BUCKET_MIN and len(nonempty) >= 2 and top < BLOB_MAX,
    }


def _hit(rows: list[dict], key: str) -> dict:
    n = len(rows)
    k = sum(1 for r in rows if r[key])
    return {"n": n, "k": k, "rate": round(k / n, 6) if n else None}


def write_result(rows: list[dict], missing: int, row_mismatch: int, n_15m: int, n_frozen: int) -> dict:
    n = len(rows)
    by_fam = {f: [r for r in rows if r["family"] == f] for f in ("B1", "B2", "B3")}
    layer_b1 = _layers(by_fam["B1"], B12_LAYERS)
    layer_b2 = _layers(by_fam["B2"], B12_LAYERS)
    layer_b3 = _layers(by_fam["B3"], B3_LAYERS)
    b2_decide = False
    if n_15m != EXPECTED_N_15M or n_frozen != EXPECTED_N_EVENT or missing or row_mismatch or n != EXPECTED_N_EVENT:
        decision, kind = "FAIL", "CLOCK"
    elif len(by_fam["B1"]) != EXPECTED_N_B1 or len(by_fam["B2"]) != EXPECTED_N_B2 or len(by_fam["B3"]) != EXPECTED_N_B3:
        decision, kind = "FAIL", "CLOCK"
    elif layer_b1["has_layers"] or layer_b3["has_layers"]:
        decision, kind = "PASS", "HIERARCHY_CANDIDATE"
    else:
        decision, kind = "PASS", "HOLD_NO_HIERARCHY"

    fam_out = {}
    for f, sub in by_fam.items():
        order = B3_LAYERS if f == "B3" else B12_LAYERS
        fam_out[f] = {
            "n": len(sub),
            "layers": _layers(sub, order),
            "mae_close": _q([r["mae_close"] for r in sub]),
            "mae_bar": _q([r["mae_bar"] for r in sub]),
            "mae_over_box": _q([r["mae_over_box"] for r in sub]),
            "mae_over_leave": _q([r["mae_over_leave"] for r in sub]),
            "hours_to_mae": _q([r["hours_to_mae"] for r in sub if r["hours_to_mae"] is not None]),
            "hours_to_pierce_leave_ext": _q(
                [r["hours_to_pierce_leave_ext"] for r in sub if r["hours_to_pierce_leave_ext"] is not None]
            ),
            "hours_to_enter_box_ext": _q(
                [r["hours_to_enter_box_ext"] for r in sub if r["hours_to_enter_box_ext"] is not None]
            ),
            "hours_to_through_far_ext": _q(
                [r["hours_to_through_far_ext"] for r in sub if r["hours_to_through_far_ext"] is not None]
            ),
            "hours_available": _q([r["hours_available"] for r in sub]),
            "pierce_leave_ext": _hit(sub, "pierce_leave_ext"),
            "pierce_leave_close": _hit(sub, "pierce_leave_close"),
            "enter_box_ext": _hit(sub, "enter_box_ext"),
            "enter_box_close": _hit(sub, "enter_box_close"),
            "through_far_ext": _hit(sub, "through_far_ext"),
            "enter_leave": _hit(sub, "enter_leave"),
            "t0_overlap_leave": _hit(sub, "t0_overlap_leave"),
            "t0_in_box": _hit(sub, "t0_in_box"),
            "t0_overlap_box": _hit(sub, "t0_overlap_box"),
        }

    result = {
        "decision": decision,
        "kind": kind,
        "n_event": n,
        "missing_anchor": missing,
        "tape_row_mismatch": row_mismatch,
        "bucket_min": BUCKET_MIN,
        "blob_max": BLOB_MAX,
        "b2_decides_hierarchy": b2_decide,
        "all": {
            "mae_close": _q([r["mae_close"] for r in rows]),
            "mae_bar": _q([r["mae_bar"] for r in rows]),
            "mae_over_box": _q([r["mae_over_box"] for r in rows]),
            "mae_over_leave": _q([r["mae_over_leave"] for r in rows]),
            "hours_to_mae": _q([r["hours_to_mae"] for r in rows if r["hours_to_mae"] is not None]),
            "hours_to_pierce_leave_ext": _q(
                [r["hours_to_pierce_leave_ext"] for r in rows if r["hours_to_pierce_leave_ext"] is not None]
            ),
            "hours_to_enter_box_ext": _q(
                [r["hours_to_enter_box_ext"] for r in rows if r["hours_to_enter_box_ext"] is not None]
            ),
            "hours_to_through_far_ext": _q(
                [r["hours_to_through_far_ext"] for r in rows if r["hours_to_through_far_ext"] is not None]
            ),
            "pierce_leave_ext": _hit(rows, "pierce_leave_ext"),
            "enter_box_ext": _hit(rows, "enter_box_ext"),
            "through_far_ext": _hit(rows, "through_far_ext"),
        },
        "by_family": fam_out,
        "hierarchy_b1": layer_b1,
        "hierarchy_b2": layer_b2,
        "hierarchy_b3": layer_b3,
        "blocked": (
            "无 ATR 阈值。无止损优化。无收益率。无 EMA/OF。无 Fate/Continuation 回调。"
            "MAE 扫到样本末，不是局部失效深度。只读首次穿锚时间。"
            "B1/B2 的 enter_box/through_far 不是反向失效（T0 多已在盒外）。"
            "合样本 pierce/box/far 不准当层级。"
            "HIERARCHY_CANDIDATE ≠ 失效边界。第二闸另授权。"
            "HOLD_NO_HIERARCHY → 本线关闭，不准补 ATR。"
        ),
    }
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2) + "\n")
    (LOG / "EVENTS.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    lines = [
        f"CHAN_PENETRATION_CENSUS_001  decision={decision}  kind={kind}",
        "确认后反向 excursion / 冻结结构锚。无 ATR。无止损。无 PnL。",
        "",
        f"  n={n} missing={missing} row_mismatch={row_mismatch}",
        f"  mae_close={result['all']['mae_close']}",
        f"  hours_to_mae={result['all']['hours_to_mae']}  (扫到样本末，不是局部失效深度)",
        f"  hours_to_pierce_leave={result['all']['hours_to_pierce_leave_ext']}",
        "",
    ]
    for f in ("B1", "B2", "B3"):
        d = fam_out[f]
        lines.append(
            f"  {f} n={d['n']} layers={d['layers']['counts']} visible={d['layers']['visible']} "
            f"top={d['layers']['top_share']} has_layers={d['layers']['has_layers']}"
        )
        lines.append(
            f"      leave_ext={d['pierce_leave_ext']} box_ext={d['enter_box_ext']} far={d['through_far_ext']}"
        )
        lines.append(
            f"      h_leave={d['hours_to_pierce_leave_ext']} h_box={d['hours_to_enter_box_ext']} "
            f"h_far={d['hours_to_through_far_ext']}"
        )
    lines += ["", result["blocked"]]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")
    return result


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    frozen = load_events(CONT)
    anchors = {e["event_id"]: e for e in scan_anchors(bar)["events"]}
    rows = []
    missing = row_mismatch = 0
    for ev in frozen:
        eid = ev["event_id"]
        src = anchors.get(eid)
        if src is None:
            missing += 1
            continue
        if int(src["tape_row"]) != int(ev["tape_row"]):
            row_mismatch += 1
            continue
        rec = {
            "event_id": eid,
            "kind": ev["kind"],
            "zg": src["zg"],
            "zd": src["zd"],
            "leave_low": src["leave_low"],
            "leave_high": src["leave_high"],
            "tape_row": int(ev["tape_row"]),
        }
        rows.append(follow_penetration(rec, bar))
    write_result(rows, missing, row_mismatch, len(bar), len(frozen))


if __name__ == "__main__":
    main()
