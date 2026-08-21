#!/usr/bin/env python3
"""
Metric Reconciliation v0.1 (MATCHED only)

Confirms consistency between:
  - "MakerAlpha" reported in v0.1 research (return space)
  - "Gross markout @30s" in Economic Attribution (dollar space)
  - realized component used in Economic Attribution

Key point:
  Same definition may flip sign depending on weighting:
    fill-weighted mean return vs notional-weighted dollar markout

This script is read-only: it does NOT change any strategy/execution.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reconcile_fills import load_local_fills, match, normalize_local, normalize_venue  # noqa: E402


def _load_jsonl_df(log_dir: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for f in sorted(log_dir.glob("*.jsonl")):
        if f.name.startswith(("Account_", "Maker_", "RECON")):
            continue
        for line in f.open():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if isinstance(e, dict):
                rows.append(e)
    return pd.DataFrame(rows)


def _fav_ret(side: pd.Series, fill: pd.Series, px: pd.Series) -> pd.Series:
    # return space, signed by side
    fill = pd.to_numeric(fill, errors="coerce")
    px = pd.to_numeric(px, errors="coerce")
    raw = (px - fill) / fill
    return pd.Series(np.where(side == "long", raw, -raw), index=side.index)


def _weighted_mean(x: pd.Series, w: pd.Series) -> float | None:
    xx = pd.to_numeric(x, errors="coerce")
    ww = pd.to_numeric(w, errors="coerce")
    mask = xx.notna() & ww.notna()
    xx = xx[mask]
    ww = ww[mask]
    if xx.empty:
        return None
    sw = float(ww.sum())
    if sw == 0:
        return None
    return float((xx * ww).sum() / sw)


def _cluster_weight(paths: pd.DataFrame) -> pd.Series:
    if "event_cluster_id" not in paths.columns:
        return pd.Series(1.0, index=paths.index)
    cnt = paths.groupby("event_cluster_id")["event_cluster_id"].transform("count")
    return 1.0 / cnt.clip(lower=1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Economic Metric Reconciliation v0.1")
    ap.add_argument("--dir", default=str(ROOT / "logs" / "maker_edge"))
    ap.add_argument("--out", default=str(ROOT / "logs" / "maker_edge" / "Economic_Metric_Reconciliation_v0_1.txt"))
    ap.add_argument("--venue-trades", default=str(ROOT / "logs" / "maker_edge" / "venue_trades.json"))
    ap.add_argument("--matched-take", type=int, default=3890)
    args = ap.parse_args()

    log_dir = Path(args.dir)
    venue_trades_path = Path(args.venue_trades)

    df = _load_jsonl_df(log_dir)
    fills = df[df["event"] == "fill"].copy() if "event" in df.columns else pd.DataFrame()
    paths = df[df["event"] == "fill_path"].copy() if "event" in df.columns else pd.DataFrame()

    # Hard matched population via RECON-02/03 evidence: use existing matcher logic.
    venue_trades = json.loads(venue_trades_path.read_text())
    local_fills_raw = load_local_fills(log_dir)
    locals_norm = [normalize_local(e, i) for i, e in enumerate(local_fills_raw)]
    venues_norm = [normalize_venue(t, i) for i, t in enumerate(venue_trades)]
    recon = match(locals_norm, venues_norm)

    matched_fill_ids = {m["local"]["fill_id"] for m in recon["matched"]}
    matched_trade_ids = {m["venue"]["venue_trade_id"] for m in recon["matched"]}

    fills = fills[fills["fill_id"].isin(matched_fill_ids)].copy()
    paths = paths[paths["fill_id"].isin(matched_fill_ids)].copy()

    # Build after_30s already present in fill_path fields.
    # MakerAlpha in analyze_maker_edge uses after_30s_price and _fav_ret definition.
    # We'll recompute:
    #   return space:
    #     maker_alpha_fill_weighted = mean(markout_30s)
    #     maker_alpha_notional_weighted_return = (gross_markout_usdt / total_notional)
    #     gross_markout_usdt = sum(notional * markout_30s)
    #
    if paths.empty:
        raise SystemExit("No matched paths loaded")

    # Merge meta from fills (side, fill_price, event_cluster_id, notional proxy)
    meta_cols = [
        c
        for c in [
            "fill_id",
            "side",
            "fill_price",
            "amount",
            "event_cluster_id",
            "spread_capture_pct",
            "pair",
        ]
        if c in fills.columns
    ]
    meta = fills.drop_duplicates("fill_id")[meta_cols]
    paths = paths.merge(meta, on="fill_id", how="left", suffixes=("", "_m"))

    # If fill_path already had these columns, merge created *_m alternates.
    for col in ["side", "fill_price", "amount", "event_cluster_id"]:
        alt = f"{col}_m"
        if alt in paths.columns:
            if col not in paths.columns:
                paths[col] = paths[alt]
            else:
                paths[col] = paths[col].fillna(paths[alt])

    # Ensure required fields
    paths["side"] = paths["side"].astype(str)
    paths["fill_price"] = pd.to_numeric(paths["fill_price"], errors="coerce")
    paths["qty"] = pd.to_numeric(paths["amount"], errors="coerce")
    paths["notional_usdt"] = paths["fill_price"] * paths["qty"]
    paths["after_30s_price"] = pd.to_numeric(paths["after_30s_price"], errors="coerce")

    paths["markout_30s_return"] = _fav_ret(paths["side"], paths["fill_price"], paths["after_30s_price"])

    gross_markout_usdt = float((paths["notional_usdt"] * paths["markout_30s_return"]).sum())
    total_notional = float(paths["notional_usdt"].sum())
    maker_alpha_fill_weighted = float(paths["markout_30s_return"].mean())
    maker_alpha_notional_weighted_return = float(gross_markout_usdt / total_notional) if total_notional else None

    cw = _cluster_weight(paths)
    maker_alpha_cluster_weighted_return = _weighted_mean(paths["markout_30s_return"], cw)

    # realized component from userTrades is already in Economic Attribution.
    # Here we only validate return space; realized component sign conventions are asserted elsewhere.
    out = Path(args.out)
    lines: list[str] = []

    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    p("=" * 72)
    p("Economic Metric Reconciliation v0.1 (MATCHED=3890)")
    p("=" * 72)
    p(f"Matched paths: {len(paths)}  (expected ~3886)")
    p()
    p("Definitions (same math as analyze_maker_edge):")
    p("- markout_30s_return = _fav_ret(side, fill_price, after_30s_price)")
    p("- gross_markout_usdt = sum(notional_usdt * markout_30s_return)")
    p()
    p("Return-space metrics (sign may differ due to weighting):")
    p(f"MakerAlpha fill-weighted mean return:          {_pct(maker_alpha_fill_weighted)}")
    p(f"MakerAlpha notional-weighted mean return:     {_pct(maker_alpha_notional_weighted_return)}")
    p(f"MakerAlpha cluster-weighted mean return:      {_pct(maker_alpha_cluster_weighted_return)}")
    p()
    p("Dollar-space metrics:")
    p(f"gross_markout_usdt (30s):                     {gross_markout_usdt:+.6f} USDT")
    p(f"total_notional_usdt:                         {total_notional:.3f} USDT")
    p()
    p("If fill-weighted return is + but gross_markout_usdt is negative,")
    p("it means notional weighting flips sign (alpha is conditionally realized).")
    p("=" * 72)

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


def _pct(v: float | None) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v*100:.6f}%"


if __name__ == "__main__":
    raise SystemExit(main())

