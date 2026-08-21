"""CHAN_SETUP_STRATA_001 gates. Four one-way tables. No new Setup."""
from __future__ import annotations

from chan_setup_strata.paths import EXPECTED_N_15M, EXPECTED_N_MOTHER, EXPECTED_N_OUTCOME
from chan_setup_strata.schema import FORBIDDEN_STRATA_KEYS, OUTCOME_CLASSES


def _n(table: list[dict]) -> int:
    return sum(int(r["n"]) for r in table)


def audit_strata(
    tape: list[dict],
    census: list[dict],
    outcomes: list[dict],
    rows: list[dict],
    tables: dict,
    drop: list[str],
) -> dict:
    gates = []

    def add(name: str, ok: bool, detail: str) -> None:
        gates.append({"name": name, "verdict": "PASS" if ok else "FAIL", "detail": detail})

    add("C0", len(tape) == EXPECTED_N_15M, f"n_tape={len(tape)}")
    add(
        "C1",
        len(census) == EXPECTED_N_MOTHER
        and len(outcomes) == EXPECTED_N_OUTCOME
        and len(rows) == EXPECTED_N_OUTCOME
        and len(drop) == EXPECTED_N_MOTHER - EXPECTED_N_OUTCOME,
        f"mother={len(census)} outcome={len(outcomes)} rows={len(rows)} clock_drop={len(drop)}",
    )
    drop_in = [r["setup_id"] for r in rows if r["setup_id"] in set(drop)]
    add("C2", len(drop_in) == 0 and len(drop) == 1, f"clock_drop excluded ids={drop}")

    y_ok = all(r["outcome_class"] in OUTCOME_CLASSES for r in rows)
    y_match = [r["outcome_class"] for r in rows] == [o["outcome_class"] for o in outcomes]
    add("C3", y_ok and y_match, "Y = frozen outcome_class, not recomputed")

    keys = set(tables)
    add(
        "C4",
        keys == {"htf_leftover_count", "space_relation", "bi_state", "fractal_direction"},
        f"tables={sorted(keys)}",
    )
    ns = {k: _n(v) for k, v in tables.items()}
    add("C5", all(n == EXPECTED_N_OUTCOME for n in ns.values()), f"table_n={ns}")

    anchors = [r["level"] for r in tables["htf_leftover_count"]]
    add("C6", all(isinstance(a, int) and a >= 1 for a in anchors), f"anchor_levels={anchors}")

    def _keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield str(k)
                yield from _keys(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from _keys(item)

    found = FORBIDDEN_STRATA_KEYS.intersection(_keys(tables))
    has_cross = any(k in tables for k in ("four_way", "interaction", "NEW_SETUP"))
    add("C7", not found and not has_cross, f"no hit_rate/p_value/NEW_SETUP/4-way dirty={sorted(found)}")

    fail = any(g["verdict"] != "PASS" for g in gates)
    return {
        "decision": "FAIL" if fail else "PASS",
        "kind": "CLOCK" if fail else "STRATA_OK",
        "gates": gates,
        "n_clock_drop": len(drop),
        "clock_drop_ids": drop,
        "tables": tables,
        "blocked": "不准收紧 Setup。不准研究 B1。不准 OF/SMC/MFE。下一枪未授权。",
    }
