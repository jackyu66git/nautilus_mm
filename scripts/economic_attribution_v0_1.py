#!/usr/bin/env python3
"""
Economic Attribution v0.1

Hard Evidence Population only:
  MATCHED = Local Fill ↔ Venue Trade dual evidence

Purpose:
  Economic Attribution only.
  No strategy modification.
  No live execution.
  No economic simulation.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reconcile_fills import load_local_fills, match, normalize_local, normalize_venue  # noqa: E402


def _load_jsonl_df(log_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
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


def _parse_fill_context(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "fill_context" not in df.columns:
        return pd.DataFrame(columns=["fill_id"])
    rows = []
    for _, r in df.iterrows():
        ctx = r.get("fill_context")
        if not isinstance(ctx, dict):
            continue
        rows.append(
            {
                "fill_id": r.get("fill_id"),
                "market_event_before_fill": ctx.get("market_event_before_fill"),
                "trade_imbalance_5s": ctx.get("trade_imbalance_5s"),
                "price_velocity_5s": ctx.get("price_velocity_5s"),
                "fill_type": ctx.get("fill_type"),
            }
        )
    return pd.DataFrame(rows)


def _fav_ret(side: pd.Series, fill: pd.Series, px: pd.Series) -> pd.Series:
    raw = (pd.to_numeric(px, errors="coerce") - pd.to_numeric(fill, errors="coerce")) / pd.to_numeric(
        fill, errors="coerce"
    )
    return pd.Series(np.where(side == "long", raw, -raw), index=side.index)


def _cluster_weight(frame: pd.DataFrame) -> pd.Series:
    cnt = frame.groupby("event_cluster_id")["event_cluster_id"].transform("count")
    return 1.0 / cnt.clip(lower=1)


def _pct(v: float | None) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v * 100:.4f}%"


def _num(v: float | None, digits: int = 4) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v:.{digits}f}"


def _mean(s: pd.Series) -> float | None:
    s = pd.to_numeric(s, errors="coerce").dropna()
    return None if s.empty else float(s.mean())


def _sum(s: pd.Series) -> float:
    s = pd.to_numeric(s, errors="coerce").fillna(0.0)
    return float(s.sum())


def _weighted_mean(v: pd.Series, w: pd.Series) -> float | None:
    vv = pd.to_numeric(v, errors="coerce")
    ww = pd.to_numeric(w, errors="coerce").fillna(0.0)
    mask = vv.notna() & ww.notna()
    vv = vv[mask]
    ww = ww[mask]
    if vv.empty or float(ww.sum()) == 0.0:
        return None
    return float((vv * ww).sum() / ww.sum())


def _prepare_paths(paths: pd.DataFrame) -> pd.DataFrame:
    paths = paths.copy()
    if "max_price" in paths.columns and "min_price" in paths.columns and "fill_price" in paths.columns:
        rng = (pd.to_numeric(paths["max_price"], errors="coerce") - pd.to_numeric(paths["min_price"], errors="coerce")) / pd.to_numeric(
            paths["fill_price"], errors="coerce"
        )
        med = float(rng.dropna().median()) if rng.notna().any() else 0.0
        paths["vol_bucket"] = np.where(rng >= med, "high_vol", "low_vol")
    if "price_velocity_5s" in paths.columns and pd.to_numeric(paths["price_velocity_5s"], errors="coerce").notna().any():
        v = pd.to_numeric(paths["price_velocity_5s"], errors="coerce")
        thr = float(v.abs().median()) * 0.5
        paths["trend_bucket"] = np.where(v > thr, "trend_up", np.where(v < -thr, "trend_down", "range"))
    if "spread" in paths.columns and "fill_price" in paths.columns and pd.to_numeric(paths["spread"], errors="coerce").notna().any():
        sp = pd.to_numeric(paths["spread"], errors="coerce") / pd.to_numeric(paths["fill_price"], errors="coerce")
        med = float(sp.dropna().median()) if sp.notna().any() else 0.0
        paths["liq_bucket"] = np.where(sp <= med, "tight_spread", "wide_spread")
    paths["toxicity_bucket"] = np.where(paths["path_type"].astype(str).str.startswith("C"), "toxic", "non_toxic")
    return paths


def _inventory_metrics(matched: pd.DataFrame) -> dict[str, float | None]:
    if matched.empty:
        return {}
    g = matched.sort_values("venue_time_ms").copy()
    g["signed_qty"] = np.where(g["side"] == "long", g["qty"], -g["qty"])
    g["net_btc"] = g["signed_qty"].cumsum()
    g["abs_net_btc"] = g["net_btc"].abs()
    times = pd.to_numeric(g["venue_time_ms"], errors="coerce").astype("float64") / 1000.0
    dt = times.shift(-1) - times
    dt = dt.fillna(0.0).clip(lower=0.0)
    total_t = float(dt.sum())
    tw_abs = float((g["abs_net_btc"] * dt).sum() / total_t) if total_t > 0 else None
    tw_signed = float((g["net_btc"] * dt).sum() / total_t) if total_t > 0 else None
    return {
        "max_net_btc": float(g["net_btc"].max()),
        "min_net_btc": float(g["net_btc"].min()),
        "max_abs_net_btc": float(g["abs_net_btc"].max()),
        "avg_abs_net_btc_per_fill": float(g["abs_net_btc"].mean()),
        "time_weighted_abs_net_btc": tw_abs,
        "time_weighted_signed_net_btc": tw_signed,
        "long_qty": float(g.loc[g["signed_qty"] > 0, "signed_qty"].sum()),
        "short_qty": float((-g.loc[g["signed_qty"] < 0, "signed_qty"]).sum()),
        "turnover_btc": float(g["qty"].sum()),
    }


def _bucket_table(paths: pd.DataFrame, bucket: str, title: str) -> list[dict[str, Any]]:
    if bucket not in paths.columns or paths.empty:
        return []
    rows = []
    for key, grp in paths.groupby(bucket):
        notional = grp["notional_usdt"].sum()
        clusters = grp["event_cluster_id"].nunique()
        rows.append(
            {
                "dimension": title,
                "bucket": str(key),
                "fills": int(len(grp)),
                "clusters": int(clusters),
                "btc_qty": float(grp["qty"].sum()),
                "notional_usdt": float(notional),
                "fee_usdt": float(grp["commission_usdt"].sum()),
                "fee_per_fill": float(grp["commission_usdt"].mean()) if len(grp) else None,
                "fee_per_btc": float(grp["commission_usdt"].sum() / grp["qty"].sum()) if grp["qty"].sum() else None,
                "markout_1s": _weighted_mean(grp["markout_1s"], grp["notional_usdt"]),
                "markout_5s": _weighted_mean(grp["markout_5s"], grp["notional_usdt"]),
                "markout_10s": _weighted_mean(grp["markout_10s"], grp["notional_usdt"]),
                "markout_30s": _weighted_mean(grp["markout_30s"], grp["notional_usdt"]),
                "markout_300s": _weighted_mean(grp["markout_300s"], grp["notional_usdt"]),
                "gross_markout_30s_usdt": float(grp["gross_markout_30s_usdt"].sum()),
                "realized_pnl_usdt": float(grp["realized_pnl_usdt"].sum()),
                "net_attr_30s_usdt": float(grp["net_attr_30s_usdt"].sum()),
            }
        )
    rows.sort(key=lambda x: (-x["fills"], x["bucket"]))
    return rows


def _counterfactual(base: pd.DataFrame, exclude_col: str, exclude_values: set[str], label: str) -> dict[str, Any]:
    kept = base[~base[exclude_col].astype(str).isin(exclude_values)].copy()
    return {
        "name": label,
        "fills": int(len(kept)),
        "clusters": int(kept["event_cluster_id"].nunique()) if not kept.empty else 0,
        "btc_qty": float(kept["qty"].sum()) if not kept.empty else 0.0,
        "fee_usdt": float(kept["commission_usdt"].sum()) if not kept.empty else 0.0,
        "gross_markout_30s_usdt": float(kept["gross_markout_30s_usdt"].sum()) if not kept.empty else 0.0,
        "realized_pnl_usdt": float(kept["realized_pnl_usdt"].sum()) if not kept.empty else 0.0,
        "net_attr_30s_usdt": float(kept["net_attr_30s_usdt"].sum()) if not kept.empty else 0.0,
        "markout_30s": _weighted_mean(kept["markout_30s"], kept["notional_usdt"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Economic Attribution v0.1 (MATCHED only)")
    ap.add_argument("--dir", default=str(ROOT / "logs" / "maker_edge"))
    ap.add_argument("--out", default=str(ROOT / "logs" / "maker_edge" / "Economic_Attribution_v0_1.txt"))
    ap.add_argument("--recon03", default=str(ROOT / "logs" / "maker_edge" / "RECONCILIATION_03.json"))
    ap.add_argument("--account", default=str(ROOT / "logs" / "maker_edge" / "Account_Reconciliation.json"))
    ap.add_argument("--venue-trades", default=str(ROOT / "logs" / "maker_edge" / "venue_trades.json"))
    args = ap.parse_args()

    log_dir = Path(args.dir)
    df = _load_jsonl_df(log_dir)
    fills = df[df["event"] == "fill"].copy()
    paths = df[df["event"] == "fill_path"].copy()
    inv = df[df["event"] == "inventory_tick"].copy()

    venue_trades = json.loads(Path(args.venue_trades).read_text())
    local_fills_raw = load_local_fills(log_dir)
    locals_norm = [normalize_local(e, i) for i, e in enumerate(local_fills_raw)]
    venues_norm = [normalize_venue(t, i) for i, t in enumerate(venue_trades)]
    recon = match(locals_norm, venues_norm)
    matched_fill_ids = {m["local"]["fill_id"] for m in recon["matched"]}
    matched_trade_ids = {m["venue"]["venue_trade_id"] for m in recon["matched"]}

    fills = fills[fills["fill_id"].isin(matched_fill_ids)].copy()
    paths = paths[paths["fill_id"].isin(matched_fill_ids)].copy()

    fc = _parse_fill_context(fills)
    meta_cols = [
        c
        for c in [
            "fill_id",
            "side",
            "fill_price",
            "spread",
            "spread_capture_pct",
            "obi",
            "trade_imbalance",
            "bid_depth_5",
            "ask_depth_5",
            "book_age_ms",
            "inventory",
            "inventory_time",
            "inventory_skew",
            "pre_5s_deteriorated",
            "mid",
            "event_cluster_id",
            "pair",
        ]
        if c in fills.columns
    ]
    meta = fills.drop_duplicates("fill_id")[meta_cols]
    paths = paths.merge(meta, on="fill_id", how="left", suffixes=("", "_f"))
    for col in ["event_cluster_id", "side", "fill_price", "spread_capture_pct", "mid"]:
        alt = f"{col}_f"
        if alt in paths.columns:
            if col not in paths.columns:
                paths[col] = paths[alt]
            else:
                paths[col] = paths[col].fillna(paths[alt])
    if not fc.empty:
        paths = paths.merge(fc, on="fill_id", how="left")
    paths = _prepare_paths(paths)

    venue = pd.DataFrame(venues_norm)
    venue = venue[venue["venue_trade_id"].isin(matched_trade_ids)].copy()
    venue = venue.rename(
        columns={
            "venue_trade_id": "trade_id_link",
            "venue_order_id": "venue_order_id",
            "qty": "qty",
            "px": "venue_price",
            "ts": "venue_ts",
        }
    )
    raw_v = pd.DataFrame(venue_trades)
    raw_v["trade_id_link"] = raw_v["id"].astype(str)
    raw_v["venue_order_id"] = raw_v["orderId"].astype(str)
    raw_v["commission_usdt"] = pd.to_numeric(raw_v["commission"], errors="coerce")
    raw_v["realized_pnl_usdt"] = pd.to_numeric(raw_v["realizedPnl"], errors="coerce").fillna(0.0)
    raw_v["venue_time_ms"] = pd.to_numeric(raw_v["time"], errors="coerce")
    raw_v["qty"] = pd.to_numeric(raw_v["qty"], errors="coerce")
    raw_v["venue_price"] = pd.to_numeric(raw_v["price"], errors="coerce")
    raw_v["side"] = np.where(raw_v["buyer"].astype(bool), "long", "short")
    raw_v = raw_v[raw_v["trade_id_link"].isin(matched_trade_ids)].copy()

    matched_map = pd.DataFrame(
        [
            {
                "fill_id": m["local"]["fill_id"],
                "trade_id_link": m["venue"]["venue_trade_id"],
                "venue_order_id": m["venue"]["venue_order_id"],
            }
            for m in recon["matched"]
        ]
    )

    paths = paths.merge(
        matched_map.merge(
            raw_v[
                [
                    "trade_id_link",
                    "venue_order_id",
                    "commission_usdt",
                    "realized_pnl_usdt",
                    "venue_time_ms",
                    "qty",
                    "venue_price",
                    "side",
                ]
            ],
            on=["trade_id_link", "venue_order_id"],
            how="left",
        ),
        on="fill_id",
        how="left",
        suffixes=("", "_venue"),
    )

    paths["fill_price"] = pd.to_numeric(paths["fill_price"], errors="coerce")
    paths["qty"] = pd.to_numeric(paths["qty"], errors="coerce")
    paths["notional_usdt"] = paths["fill_price"] * paths["qty"]
    for sec, col in [(1, "after_1s_price"), (5, "after_5s_price"), (10, "after_10s_price"), (30, "after_30s_price"), (300, "after_5m_price")]:
        paths[f"markout_{sec}s"] = _fav_ret(paths["side"], paths["fill_price"], paths[col])
    paths["gross_markout_30s_usdt"] = paths["notional_usdt"] * paths["markout_30s"]
    paths["net_attr_30s_usdt"] = (
        paths["gross_markout_30s_usdt"]
        - pd.to_numeric(paths["commission_usdt"], errors="coerce").fillna(0.0)
        + pd.to_numeric(paths["realized_pnl_usdt"], errors="coerce").fillna(0.0)
    )

    inventory_metrics = _inventory_metrics(
        raw_v[
            ["venue_time_ms", "side", "qty", "commission_usdt", "realized_pnl_usdt", "venue_order_id", "trade_id_link"]
        ].copy()
    )

    n_matched_paths = len(paths)
    n_matched_fills = len(fills)
    n_matched_clusters = int(fills["event_cluster_id"].nunique()) if not fills.empty else 0
    cluster_w = _cluster_weight(paths) if not paths.empty and "event_cluster_id" in paths.columns else pd.Series(dtype=float)

    horizon_rows = []
    for sec in (1, 5, 10, 30, 300):
        col = f"markout_{sec}s"
        valid = paths[col].notna()
        sub = paths[valid]
        w = sub["notional_usdt"]
        horizon_rows.append(
            {
                "horizon": f"{sec}s",
                "n": int(len(sub)),
                "fill_w": _weighted_mean(sub[col], w),
                "cluster_w": _weighted_mean(sub[col], _cluster_weight(sub) if not sub.empty else pd.Series(dtype=float)),
                "gross_usdt": float((sub["notional_usdt"] * sub[col]).sum()) if not sub.empty else 0.0,
            }
        )

    fee_total = float(paths["commission_usdt"].sum())
    realized_total = float(paths["realized_pnl_usdt"].sum())
    gross_30_total = float(paths["gross_markout_30s_usdt"].sum())
    net_attr_30_total = float(paths["net_attr_30s_usdt"].sum())
    total_qty = float(paths["qty"].sum())
    total_notional = float(paths["notional_usdt"].sum())

    bucket_rows: list[dict[str, Any]] = []
    for col, title in [
        ("path_type", "PathType"),
        ("toxicity_bucket", "Toxicity"),
        ("vol_bucket", "Volatility"),
        ("liq_bucket", "Spread"),
        ("trend_bucket", "Trend"),
        ("market_event_before_fill", "FillContext"),
    ]:
        bucket_rows.extend(_bucket_table(paths, col, title))
    bucket_df = pd.DataFrame(bucket_rows)

    negative_states: set[str] = set()
    if not bucket_df.empty:
        neg = bucket_df[(bucket_df["dimension"] != "PathType") & (bucket_df["markout_30s"] < 0)]
        negative_states = set(neg["bucket"].astype(str))

    counterfactuals = [
        {
            "name": "BASELINE",
            "fills": int(len(paths)),
            "clusters": int(paths["event_cluster_id"].nunique()) if not paths.empty else 0,
            "btc_qty": total_qty,
            "fee_usdt": fee_total,
            "gross_markout_30s_usdt": gross_30_total,
            "realized_pnl_usdt": realized_total,
            "net_attr_30s_usdt": net_attr_30_total,
            "markout_30s": _weighted_mean(paths["markout_30s"], paths["notional_usdt"]),
        },
        _counterfactual(paths, "path_type", {"C_toxic"}, "EXCLUDE_PATH_C"),
        _counterfactual(paths, "toxicity_bucket", {"toxic"}, "EXCLUDE_TOXIC"),
        _counterfactual(paths, "market_event_before_fill", negative_states, "EXCLUDE_NEGATIVE_STATE"),
    ]

    account = json.loads(Path(args.account).read_text()) if Path(args.account).exists() else {}
    recon03 = json.loads(Path(args.recon03).read_text()) if Path(args.recon03).exists() else {}

    out_txt = Path(args.out)
    out_json = out_txt.with_suffix(".json")
    lines: list[str] = []

    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    p("=" * 72)
    p("Economic Attribution v0.1")
    p("=" * 72)
    p("Experiment: MM_EDGE_EXP_001")
    p("Population: MATCHED=3890")
    p("Strategy: v0.1 FROZEN")
    p("Execution: STOPPED")
    p("Stage3: LOCKED")
    p("Purpose: Economic Attribution only.")
    p("No strategy modification. No live execution. No economic simulation.")
    p()
    p("Layer 1 — Hard Economic Evidence")
    p("-" * 40)
    p(f"Matched fills:         {n_matched_fills}")
    p(f"Matched paths:         {n_matched_paths}")
    p(f"Matched clusters:      {n_matched_clusters}")
    p(f"Fee total:             {_num(fee_total, 6)} USDT")
    p(f"Fee / fill:            {_num(fee_total / max(n_matched_paths, 1), 6)} USDT")
    p(f"Fee / BTC:             {_num(fee_total / max(total_qty, 1e-12), 6)} USDT")
    p(f"Fee / cluster:         {_num(fee_total / max(n_matched_clusters, 1), 6)} USDT")
    p(f"Realized component:    {_num(realized_total, 6)} USDT")
    p(f"Gross markout @30s:    {_num(gross_30_total, 6)} USDT")
    p(f"Net attributable @30s: {_num(net_attr_30_total, 6)} USDT")
    p()
    p("Markout by horizon (MATCHED only)")
    p("-" * 40)
    for row in horizon_rows:
        p(
            f"{row['horizon']:>5}  n={row['n']:4d}  fill-w={_pct(row['fill_w'])}  "
            f"cluster-w={_pct(row['cluster_w'])}  gross={_num(row['gross_usdt'], 6)} USDT"
        )
    p()
    p("Inventory carry / exposure")
    p("-" * 40)
    p(f"Max net BTC:           {_num(inventory_metrics.get('max_net_btc'), 6)}")
    p(f"Min net BTC:           {_num(inventory_metrics.get('min_net_btc'), 6)}")
    p(f"Max |net BTC|:         {_num(inventory_metrics.get('max_abs_net_btc'), 6)}")
    p(f"Average |net BTC|:     {_num(inventory_metrics.get('avg_abs_net_btc_per_fill'), 6)}")
    p(f"TW |net BTC|:          {_num(inventory_metrics.get('time_weighted_abs_net_btc'), 6)}")
    p(f"TW signed net BTC:     {_num(inventory_metrics.get('time_weighted_signed_net_btc'), 6)}")
    p(f"Long qty / Short qty:  {_num(inventory_metrics.get('long_qty'), 6)} / {_num(inventory_metrics.get('short_qty'), 6)} BTC")
    p(f"Inventory turnover:    {_num(inventory_metrics.get('turnover_btc'), 6)} BTC")
    p()
    p("Slices (weighted by notional, MATCHED only)")
    p("-" * 40)
    for dim in ["PathType", "Toxicity", "Volatility", "Spread", "Trend", "FillContext"]:
        sub = bucket_df[bucket_df["dimension"] == dim].copy()
        if sub.empty:
            continue
        p(dim)
        for _, r in sub.sort_values(["fills", "bucket"], ascending=[False, True]).iterrows():
            p(
                f"  {r['bucket']}: n={int(r['fills'])} clusters={int(r['clusters'])} "
                f"fee={_num(r['fee_usdt'], 4)} gross30={_num(r['gross_markout_30s_usdt'], 4)} "
                f"realized={_num(r['realized_pnl_usdt'], 4)} net30={_num(r['net_attr_30s_usdt'], 4)} "
                f"m30={_pct(r['markout_30s'])}"
            )
        p()
    p("Layer 2 — Evidence Extension (excluded from core conclusion)")
    p("-" * 40)
    p(f"VENUE_CONFIRMED_NO_TRADE_HISTORY: {recon03.get('venue_confirmed_no_trade_history', 'n/a')}")
    p(f"VENUE_PARTIAL_ORDER_CANCELED:     {recon03.get('venue_partial_order_canceled', 'n/a')}")
    p("These rows are order-confirmed, but not part of the Hard Evidence Population.")
    p()
    p("Layer 3 — Counterfactual Attribution (NOT backtest)")
    p("-" * 40)
    p("Observed vs Exclude-Bucket Attribution. These are contribution decompositions only.")
    for row in counterfactuals:
        p(
            f"{row['name']}: fills={row['fills']} clusters={row['clusters']} "
            f"fee={_num(row['fee_usdt'], 4)} gross30={_num(row['gross_markout_30s_usdt'], 4)} "
            f"realized={_num(row['realized_pnl_usdt'], 4)} net30={_num(row['net_attr_30s_usdt'], 4)} "
            f"m30={_pct(row['markout_30s'])}"
        )
    p()
    p("Interpretation")
    p("-" * 40)
    p("Core conclusion is based on 3890 fully matched fills.")
    p("Economic Attribution asks why MakerAlpha did not convert to money.")
    p("It does NOT change quote logic, does NOT restart v0.1, and does NOT unlock Stage 3.")
    p("=" * 72)

    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sidecar = {
        "experiment_id": "MM_EDGE_EXP_001",
        "population": {
            "name": "MATCHED",
            "fills": n_matched_fills,
            "paths": n_matched_paths,
            "clusters": n_matched_clusters,
        },
        "strategy": "v0.1 FROZEN",
        "execution": "STOPPED",
        "stage3": "LOCKED",
        "fee_total_usdt": fee_total,
        "fee_per_fill_usdt": fee_total / max(n_matched_paths, 1),
        "fee_per_btc_usdt": fee_total / max(total_qty, 1e-12),
        "fee_per_cluster_usdt": fee_total / max(n_matched_clusters, 1),
        "realized_component_usdt": realized_total,
        "gross_markout_30s_usdt": gross_30_total,
        "net_attr_30s_usdt": net_attr_30_total,
        "markout_by_horizon": horizon_rows,
        "inventory_metrics": inventory_metrics,
        "bucket_rows": bucket_rows,
        "counterfactuals": counterfactuals,
        "recon03_extension": {
            "venue_confirmed_no_trade_history": recon03.get("venue_confirmed_no_trade_history"),
            "venue_partial_order_canceled": recon03.get("venue_partial_order_canceled"),
        },
        "account_recon_ref": account,
    }
    out_json.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
