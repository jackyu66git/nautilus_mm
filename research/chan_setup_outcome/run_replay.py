"""CHAN_SETUP_OUTCOME_001 Replay. Read-only Tape + frozen Census. No market rebuild."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))

from chan_setup_outcome.audit import audit_outcomes
from chan_setup_outcome.paths import CENSUS_EVENTS, LOG, TAPE
from chan_setup_outcome.scan import scan_outcomes, summarize


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    rows = _load_jsonl(TAPE)
    setups = _load_jsonl(CENSUS_EVENTS)
    records, clock_drop = scan_outcomes(rows, setups)
    summary = summarize(records, clock_drop)
    result = audit_outcomes(rows, setups, records, summary, clock_drop)
    (LOG / "OUTCOME.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (LOG / "OUTCOME_EVENTS.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in records) + ("\n" if records else "")
    )
    s = result.get("summary") or {}
    oc = s.get("outcome_class") or {}
    oe = s.get("outcome_event") or {}
    dh = s.get("duration_hours") or {}
    lines = [
        f"CHAN_SETUP_OUTCOME_001 Replay  decision={result['decision']}  kind={result['kind']}",
        "Setup_CANDIDATE 自然结构结局。不交易、不算命中率、不改分类。",
        "T_OUTCOME_VISIBLE = 出生后第一次结构事件的 Tape.t。",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    lines.append("")
    lines.append(f"  n_mother={s.get('n_mother')}")
    lines.append(f"  n_setup={s.get('n_setup')}")
    lines.append(f"  n_clock_drop={s.get('n_clock_drop')} ids={s.get('clock_drop_ids')}")
    lines.append("  outcome_class")
    for k in ("CONTINUES", "REVERSES", "DISSOLVES", "NEXT_EVENT", "CENSOR"):
        lines.append(f"    {k}={oc.get(k, 0)}")
    lines.append("  outcome_event")
    for k in ("BI_SURE_ON", "BI_DIR_CHANGE", "BI_SURE_OFF", "FX_IDENTITY_CHANGE", "CENSOR"):
        lines.append(f"    {k}={oe.get(k, 0)}")
    lines.append(f"  n_censor={s.get('n_censor')}")
    lines.append(f"  label_b1_true={s.get('label_b1_true')} label_b1_false={s.get('label_b1_false')}")
    lines.append(f"  label_b1_by_outcome_class={s.get('label_b1_by_outcome_class')}")
    lines.append(f"  label_b1_by_outcome_event={s.get('label_b1_by_outcome_event')}")
    lines.append(f"  label_b2={s.get('label_b2')}")
    lines.append(
        f"  duration_hours min={dh.get('min')} p50={dh.get('p50')} max={dh.get('max')}"
    )
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "OUTCOME.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
