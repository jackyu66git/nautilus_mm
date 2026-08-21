"""CHAN_DESK_REPLAY_001: dump 90d visible-state tape + integrity audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_desk_replay.audit import audit_tape
from chan_desk_replay.paths import AGG_DAILY, KLINE_1M, LOG, OF_1M, TAPE_END, TAPE_START
from chan_desk_replay.tape import build_tape


def _jsonable(x):
    if isinstance(x, pd.Timestamp):
        return str(x)
    return x


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    kline = pd.read_parquet(KLINE_1M)
    kline["open_ts"] = pd.to_datetime(kline["open_ts"], utc=True)
    t0, t1 = pd.Timestamp(TAPE_START), pd.Timestamp(TAPE_END)
    kline = kline[(kline["open_ts"] >= t0) & (kline["open_ts"] <= t1)]
    from chan_fractal_of.of_window import load_of_1m

    of_1m = load_of_1m(OF_1M)
    of_1m = of_1m[(of_1m["open_ts"] >= t0) & (of_1m["open_ts"] <= t1)]
    print(f"1m n={len(kline)} {kline['open_ts'].iloc[0]} → {kline['open_ts'].iloc[-1]}", flush=True)
    rows = build_tape(kline, of_1m, AGG_DAILY)
    result = audit_tape(rows)
    (LOG / "TAPE.jsonl").write_text(
        "\n".join(json.dumps({k: _jsonable(v) for k, v in r.items()}, default=str) for r in rows)
        + ("\n" if rows else "")
    )
    (LOG / "INTEGRITY.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        f"CHAN_DESK_REPLAY_001  decision={result['decision']}  kind={result['kind']}",
        "可见状态记录器。不解释、不建议、不分类、不交易。",
        "",
    ]
    for g in result["gates"]:
        lines.append(f"{g['name']:4} {g['verdict']:16} {g['detail']}")
    s = result.get("summary") or {}
    lines.append("")
    for k, v in s.items():
        lines.append(f"  {k}={v}")
    lines.append("")
    lines.append(result["blocked"])
    out = LOG / "INTEGRITY.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
