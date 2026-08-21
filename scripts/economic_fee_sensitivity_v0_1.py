#!/usr/bin/env python3
"""
Economic Fee Sensitivity v0.1 (MATCHED=3890)

Computes:
  net_attr_30s(fee_factor) = gross_markout_30s_usdt - fee_factor * fee_total_usdt + realized_component_usdt

Assumption:
  realized_component_usdt and gross_markout_30s_usdt are fixed (price/path unchanged).
  Only fee scaling is applied as a counterfactual sensitivity.

This is NOT a strategy backtest and does NOT modify any execution logic.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Economic Fee Sensitivity v0.1")
    ap.add_argument(
        "--attribution",
        default=str(ROOT / "logs" / "maker_edge" / "Economic_Attribution_v0_1.json"),
    )
    ap.add_argument(
        "--out",
        default=str(ROOT / "logs" / "maker_edge" / "Economic_Fee_Sensitivity_v0_1.txt"),
    )
    args = ap.parse_args()

    data = json.loads(Path(args.attribution).read_text())
    fee_total = float(data["fee_total_usdt"])
    realized_total = float(data["realized_component_usdt"])
    gross_markout = float(data["gross_markout_30s_usdt"])

    factors = [1.0, 0.5, 0.25, 0.1, 0.0]

    lines: list[str] = []

    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    p("=" * 72)
    p("Economic Fee Sensitivity v0.1 (MATCHED=3890)")
    p("=" * 72)
    p(f"gross_markout_30s_usdt: {gross_markout:+.6f} USDT")
    p(f"fee_total_usdt:          {fee_total:+.6f} USDT")
    p(f"realized_component_usdt:{realized_total:+.6f} USDT")
    p()
    p("Fee assumption  →  Net attributable @30s")
    p("-" * 42)

    header = ["fee_factor", "fee_usdt_assumed", "net_attr_30s_usdt"]
    p(" | ".join(header))

    for f in factors:
        fee_assumed = f * fee_total
        net = gross_markout - fee_assumed + realized_total
        row = [f"{f:.2f}", f"{fee_assumed:+.6f}", f"{net:+.6f}"]
        p(" | ".join(row))

    p()
    p("Interpretation:")
    p("- If net remains < 0 at fee_factor=0 → economics not salvageable by fee reduction alone.")
    p("- If fee reduction flips net > 0 → current venue/fee tier can be the dominant issue.")
    p("=" * 72)

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

