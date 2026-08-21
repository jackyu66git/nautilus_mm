"""CHAN_SETUP_OUTCOME_001 gates. First event only. B1 is a label."""
from __future__ import annotations

from collections import defaultdict

from chan_setup_outcome.paths import EXPECTED_N_15M, EXPECTED_N_SETUP
from chan_setup_outcome.schema import (
    FORBIDDEN_OUTCOME_KEYS,
    LABEL_B2,
    assert_outcome_clean,
    classify,
)


def audit_outcomes(
    rows: list[dict],
    setups: list[dict],
    records: list[dict],
    summary: dict,
    clock_drop: list[str],
) -> dict:
    gates = []

    def add(name: str, ok: bool, detail: str) -> None:
        gates.append({"name": name, "verdict": "PASS" if ok else "FAIL", "detail": detail})

    add("C0", len(rows) == EXPECTED_N_15M, f"n_tape={len(rows)}")
    ids_s = [s["setup_id"] for s in setups]
    ids_r = [r["setup_id"] for r in records]
    drop = list(clock_drop)
    add(
        "C1",
        len(setups) == EXPECTED_N_SETUP
        and len(records) + len(drop) == EXPECTED_N_SETUP
        and set(ids_r).isdisjoint(drop)
        and set(ids_s) == set(ids_r) | set(drop),
        f"n_setup={len(records)} n_clock_drop={len(drop)} unique={len(set(ids_r))}",
    )

    clock_ok = True
    map_ok = True
    dirty = 0
    b1_as_event = 0
    for rec in records:
        assert_outcome_clean(rec)
        if not (rec["T_SETUP_VISIBLE"] < rec["T_OUTCOME_VISIBLE"]):
            clock_ok = False
        if int(rec["outcome_row"]) <= int(rec["tape_row"]):
            clock_ok = False
        if rec["outcome_event"] == "B1_LOCK":
            b1_as_event += 1
        if FORBIDDEN_OUTCOME_KEYS.intersection(rec):
            dirty += 1
        birth_sure = bool(rows[int(rec["tape_row"])].get("ltf_bi_sure"))
        if rec["outcome_class"] != classify(rec["outcome_event"], birth_sure):
            map_ok = False
        if rec.get("label_b2") != LABEL_B2:
            map_ok = False
    add("C2", clock_ok, "T_SETUP_VISIBLE < T_OUTCOME_VISIBLE and outcome_row > tape_row")
    add("C3", map_ok and b1_as_event == 0, f"class mapping frozen b1_as_event={b1_as_event}")
    add("C4", dirty == 0, f"no WR/MFE/OF/SMC/success dirty={dirty}")

    # Same b1_lock tape row attached to at most one setup.
    owners = defaultdict(list)
    for rec in records:
        if rec["label_b1"] is not True:
            continue
        i0 = int(rec["tape_row"])
        j1 = int(rec["outcome_row"])
        for j in range(i0 + 1, j1 + 1):
            if rows[j].get("b1_lock") is True:
                owners[j].append(rec["setup_id"])
    cloned = {j: v for j, v in owners.items() if len(v) > 1}
    add("C5", len(cloned) == 0, f"b1_lock rows with >1 setup n={len(cloned)}")

    add(
        "C6",
        summary.get("n_mother") == EXPECTED_N_SETUP
        and summary.get("n_setup") == len(records)
        and summary.get("n_clock_drop") == len(drop),
        f"summary n={summary.get('n_setup')} clock_drop={summary.get('n_clock_drop')}",
    )
    add("C7", "hit_rate" not in summary and "success" not in summary, "no hit_rate/success in summary")

    fail = any(g["verdict"] != "PASS" for g in gates)
    return {
        "decision": "FAIL" if fail else "PASS",
        "kind": "CLOCK" if fail else "OUTCOME_OK",
        "gates": gates,
        "summary": summary,
        "blocked": "MFE MAE WR PF Entry OF SMC leftover分层 未跑。下一枪未授权。",
    }
