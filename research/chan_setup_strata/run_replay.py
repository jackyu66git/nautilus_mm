"""CHAN_SETUP_STRATA_001 Replay. Four one-way tables. No new Setup."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))

from chan_setup_strata.audit import audit_strata
from chan_setup_strata.paths import CENSUS_EVENTS, LOG, OUTCOME_EVENTS, TAPE
from chan_setup_strata.schema import OUTCOME_CLASSES
from chan_setup_strata.tables import build_tables, clock_drop_ids, join_rows


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _fmt_table(name: str, rows: list[dict]) -> list[str]:
    lines = [f"  {name}"]
    hdr = "    level n CONTINUES REVERSES DISSOLVES NEXT_EVENT CENSOR dissolves_share"
    lines.append(hdr)
    for r in rows:
        level = r["level"]
        share = r["dissolves_share"]
        share_s = "" if share is None else f"{share:.4f}"
        lines.append(
            f"    {level} {r['n']} "
            + " ".join(str(r[k]) for k in OUTCOME_CLASSES)
            + f" {share_s}"
        )
    return lines


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    tape = _load_jsonl(TAPE)
    census = _load_jsonl(CENSUS_EVENTS)
    outcomes = _load_jsonl(OUTCOME_EVENTS)
    drop = clock_drop_ids(census, outcomes)
    rows = join_rows(tape, outcomes)
    tables = build_tables(rows)
    result = audit_strata(tape, census, outcomes, rows, tables, drop)
    (LOG / "STRATA.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        f"CHAN_SETUP_STRATA_001 Replay  decision={result['decision']}  kind={result['kind']}",
        "出生时刻客观状态 × 已冻 Outcome。四张单维表。不收紧 Setup。",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    lines.append("")
    lines.append(f"  n_clock_drop={result.get('n_clock_drop')} ids={result.get('clock_drop_ids')}")
    lines.append("")
    for name in ("htf_leftover_count", "space_relation", "bi_state", "fractal_direction"):
        lines.extend(_fmt_table(name, tables[name]))
        lines.append("")
    lines.append(result["blocked"])
    out = LOG / "STRATA.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
