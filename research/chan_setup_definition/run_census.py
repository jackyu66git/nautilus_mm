"""CHAN_SETUP_DEFINITION_001 Census. Read-only Tape scan. No replay of market history."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))

from chan_setup_definition.audit import audit_census
from chan_setup_definition.census import scan_candidates, summarize
from chan_setup_definition.paths import LOG, TAPE


def load_tape() -> list[dict]:
    rows = []
    with TAPE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    rows = load_tape()
    events = scan_candidates(rows)
    summary = summarize(rows, events)
    result = audit_census(rows, events, summary)
    (LOG / "CENSUS.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (LOG / "CENSUS_EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in events) + ("\n" if events else "")
    )
    lines = [
        f"CHAN_SETUP_DEFINITION_001 Census  decision={result['decision']}  kind={result['kind']}",
        "Setup_CANDIDATE 观察状态普查。不解释、不买卖、不看盈亏。",
        "T_SETUP_VISIBLE = Tape 上行序第一次出现该 ltf_fx_id 的 t。",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    s = result.get("summary") or {}
    lines.append("")
    lines.append(f"  n_setup={s.get('n_setup')}")
    lines.append(f"  per_day={s.get('per_day')}")
    lines.append(f"  per_1000_bars={s.get('per_1000_bars')}")
    lines.append(f"  n_tape_rows={s.get('n_tape_rows')} span_days={s.get('span_days')}")
    lines.append(f"  n_unique_fx_id={s.get('n_unique_fx_id')}")
    lines.append(f"  n_fx_id_consumed_leftover0={s.get('n_fx_id_consumed_leftover0')}")
    lines.append(f"  n_rows_leftover_ge1={s.get('n_rows_leftover_ge1')}")
    dh = s.get("duration_hours") or {}
    db = s.get("duration_bars") or {}
    ih = s.get("interval_hours") or {}
    lines.append(f"  duration_hours min={dh.get('min')} p50={dh.get('p50')} max={dh.get('max')}")
    lines.append(f"  duration_bars min={db.get('min')} p50={db.get('p50')} max={db.get('max')}")
    lines.append(f"  interval_hours min={ih.get('min')} p50={ih.get('p50')} max={ih.get('max')}")
    lines.append(f"  htf_anchor_count_at_birth={s.get('htf_anchor_count_at_birth')}")
    lines.append(f"  ltf_fx_at_birth={s.get('ltf_fx_at_birth')}")
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
