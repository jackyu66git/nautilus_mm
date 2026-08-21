"""Census gates. First-seen is Tape row order. No outcomes."""
from __future__ import annotations

from chan_setup_definition.census import scan_candidates
from chan_setup_definition.paths import EXPECTED_N_15M, SPAN_DAYS
from chan_setup_definition.schema import FORBIDDEN_CENSUS_KEYS, assert_census_clean


def _first_row_by_fx_id(rows: list[dict]) -> dict[str, int]:
    first: dict[str, int] = {}
    for i, row in enumerate(rows):
        fx_id = row.get("ltf_fx_id")
        fx = row.get("ltf_fx")
        if not fx_id or fx not in ("TOP", "BOTTOM"):
            continue
        key = str(fx_id)
        if key not in first:
            first[key] = i
    return first


def audit_census(rows: list[dict], events: list[dict], summary: dict) -> dict:
    gates = []

    def add(name: str, ok: bool, detail: str) -> None:
        gates.append({"name": name, "verdict": "PASS" if ok else "FAIL", "detail": detail})

    n = len(rows)
    ts = [r.get("t") for r in rows]
    add("C0", n == EXPECTED_N_15M and len(set(ts)) == n, f"n={n} unique_t={len(set(ts))}")

    first = _first_row_by_fx_id(rows)
    row_ok = True
    leak_n = 0
    leftover0_born = 0
    for e in events:
        assert_census_clean(e)
        sid = e["setup_id"]
        i = first.get(sid)
        if i is None or i != int(e["tape_row"]) or str(rows[i]["t"]) != e["T_SETUP_VISIBLE"]:
            row_ok = False
            leak_n += 1
        if int(rows[int(e["tape_row"])].get("htf_anchor_count") or 0) < 1:
            leftover0_born += 1
    add("C1", row_ok and leak_n == 0, f"T_SETUP_VISIBLE=first Tape row of ltf_fx_id leak_n={leak_n}")
    add("C2", leftover0_born == 0, f"birth leftover>=1 leftover0_born={leftover0_born}")

    ids = [e["setup_id"] for e in events]
    add("C3", len(ids) == len(set(ids)), f"unique setup_id n={len(ids)} unique={len(set(ids))}")

    dirty = 0
    for e in events:
        if FORBIDDEN_CENSUS_KEYS.intersection(e):
            dirty += 1
    add("C4", dirty == 0, f"no WR/MFE/OF/SMC/B1/T_FX_VISIBLE dirty={dirty}")

    # Independent rescan must match. Proves we did not use T_FX_VISIBLE.
    replayed = scan_candidates(rows)
    match = [a["setup_id"] for a in replayed] == ids
    vis_match = [a["T_SETUP_VISIBLE"] for a in replayed] == [e["T_SETUP_VISIBLE"] for e in events]
    add("C5", match and vis_match, f"row-order rescan n={len(replayed)}")

    add("C6", summary.get("span_days") == SPAN_DAYS, f"span_days={summary.get('span_days')}")

    fail = any(g["verdict"] != "PASS" for g in gates)
    return {
        "decision": "FAIL" if fail else "PASS",
        "kind": "CLOCK" if fail else "CENSUS_OK",
        "gates": gates,
        "summary": summary,
        "blocked": "MFE MAE WR PF Entry OF SMC B1→B2 阈值 未跑。下一枪未授权。",
    }
