"""CHAN_3RD_POINT_001 Census. Online 3rd-class BSP. No P&L."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT.parent / "user_data" / "Chan"))

from chan_3rd_point.paths import EXPECTED_N_15M, KLINE_1M, LOG
from chan_3rd_point.scan import audit, scan_third
from chan_fractal_of.clock import resample_bars


def main() -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    bar = resample_bars(pd.read_parquet(KLINE_1M), 15)
    payload = scan_third(bar)
    result = audit(payload)
    if payload["n_15m"] != EXPECTED_N_15M:
        result["decision"] = "FAIL"
        result["kind"] = "CLOCK"
    (LOG / "CENSUS.json").write_text(
        json.dumps({k: v for k, v in result.items()}, indent=2, default=str) + "\n"
    )
    (LOG / "EVENTS.jsonl").write_text(
        "\n".join(json.dumps(e, default=str) for e in payload["events"])
        + ("\n" if payload["events"] else "")
    )
    lines = [
        f"CHAN_3RD_POINT_001 Census  decision={result['decision']}  kind={result['kind']}",
        "15m 同级别第三类买卖点。T_ZS < T_LEAVE < T_3。回抽后是否再进中枢不用于定义。",
        "",
        f"  n_15m={payload['n_15m']} n_zs={result['n_zs']} n_zs_complete={result['n_zs_complete']} n_leave={result['n_leave']}",
        f"  n_b3={result['n_b3']} n_s3={result['n_s3']} n_3={result['n_3']}",
        f"  n_pullback_in={result['n_pullback_in']} n_wrong_dir={result['n_wrong_dir']} n_drop={result['n_drop']} n_waiting_pb={result['n_waiting_pb']}",
        f"  clock_ok={result['clock_ok']}",
        f"  leave_to_3_hours_p50={result['leave_to_3_hours_p50']}",
        "",
        "离开=成员后第一笔确认的方向突破（可重叠中枢）。回抽未进才是 T_3。",
        result["blocked"],
    ]
    out = LOG / "CENSUS.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text(), end="")


if __name__ == "__main__":
    main()
