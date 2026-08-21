#!/usr/bin/env python3
"""
Prefill Adverse-Selection Attribution v0.1

Experiment: MM_EDGE_EXP_001
Population: frozen historical fills
Strategy: v0.1 FROZEN
Execution: STOPPED
Purpose:
    Pre-fill adverse-selection predictability audit
NOT:
    strategy
    backtest
    optimization
    model training

Hard contract:
    feature_timestamp <= t_fill - margin_sec

This script intentionally prefers strict no-leakage over feature richness.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
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


def _pct(v: float | None) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v*100:.2f}%"


def _num(v: float | None, digits: int = 4) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v:.{digits}f}"


def _fav_ret(side: pd.Series, fill: pd.Series, px: pd.Series) -> pd.Series:
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
    if sw == 0.0:
        return None
    return float((xx * ww).sum() / sw)


def _sample_grade(n: int) -> str:
    if n < 30:
        return "LOW_N"
    if n < 100:
        return "WEAK_EVIDENCE"
    return "USABLE"


def _grade_probability(delta_pp: float, n_best: int) -> str:
    if n_best < 30:
        return "LOW_N"
    if delta_pp < 5.0:
        return "NO_PREFILL_SIGNAL"
    if n_best < 100 or delta_pp < 10.0:
        return "STATISTICAL_SIGNAL_ONLY"
    return "CANDIDATE_V0_2_SIGNAL"


def _grade_economic(delta_usdt_per_fill: float, n_best: int) -> str:
    if n_best < 30:
        return "LOW_N"
    if abs(delta_usdt_per_fill) < 0.003:
        return "NO_PREFILL_SIGNAL"
    if n_best < 100 or abs(delta_usdt_per_fill) < 0.008:
        return "STATISTICAL_SIGNAL_ONLY"
    return "CANDIDATE_V0_2_SIGNAL"


def _state_table_num(df: pd.DataFrame, feature: str, labels: list[str]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    s = pd.to_numeric(df[feature], errors="coerce")
    valid = df[s.notna()].copy()
    valid[feature] = s[s.notna()]
    if valid.empty:
        return [], {k: "NO_DATA" for k in labels + ["Economic"]}
    q30 = float(valid[feature].quantile(0.30))
    q70 = float(valid[feature].quantile(0.70))
    # if no spread, collapse
    if math.isclose(q30, q70):
        valid["_state"] = "all"
    else:
        valid["_state"] = np.where(
            valid[feature] <= q30,
            "low",
            np.where(valid[feature] >= q70, "high", "mid"),
        )
    base = {
        lab: float(valid[lab].mean()) for lab in labels
    }
    base["economic_mean"] = float(valid["net_attr_30s_usdt"].mean())
    rows = []
    grades: dict[str, str] = {}
    for state, g in valid.groupby("_state"):
        row = {
            "feature": feature,
            "state": str(state),
            "n": int(len(g)),
            "sample_grade": _sample_grade(int(len(g))),
            "median": float(g[feature].median()),
            "p25": float(g[feature].quantile(0.25)),
            "p75": float(g[feature].quantile(0.75)),
            "net_attr_mean": float(g["net_attr_30s_usdt"].mean()),
        }
        for lab in labels:
            row[f"p_{lab}"] = float(g[lab].mean())
            row[f"delta_{lab}_pp"] = (row[f"p_{lab}"] - base[lab]) * 100.0
        row["delta_economic_per_fill"] = row["net_attr_mean"] - base["economic_mean"]
        rows.append(row)

    # grade by strongest state-vs-baseline shift
    for lab in labels:
        best = max(rows, key=lambda r: abs(r[f"delta_{lab}_pp"]))
        grades[lab] = _grade_probability(abs(best[f"delta_{lab}_pp"]), int(best["n"]))
    best_e = max(rows, key=lambda r: abs(r["delta_economic_per_fill"]))
    grades["Economic"] = _grade_economic(abs(best_e["delta_economic_per_fill"]), int(best_e["n"]))
    return rows, grades


def _state_table_cat(df: pd.DataFrame, feature: str, labels: list[str]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    valid = df[df[feature].notna()].copy()
    if valid.empty:
        return [], {k: "NO_DATA" for k in labels + ["Economic"]}
    base = {
        lab: float(valid[lab].mean()) for lab in labels
    }
    base["economic_mean"] = float(valid["net_attr_30s_usdt"].mean())
    rows = []
    grades: dict[str, str] = {}
    for state, g in valid.groupby(feature):
        n = int(len(g))
        row = {
            "feature": feature,
            "state": str(state),
            "n": n,
            "sample_grade": _sample_grade(n),
            "median": None,
            "p25": None,
            "p75": None,
            "net_attr_mean": float(g["net_attr_30s_usdt"].mean()),
        }
        for lab in labels:
            row[f"p_{lab}"] = float(g[lab].mean())
            row[f"delta_{lab}_pp"] = (row[f"p_{lab}"] - base[lab]) * 100.0
        row["delta_economic_per_fill"] = row["net_attr_mean"] - base["economic_mean"]
        rows.append(row)
    for lab in labels:
        best = max(rows, key=lambda r: abs(r[f"delta_{lab}_pp"]))
        grades[lab] = _grade_probability(abs(best[f"delta_{lab}_pp"]), int(best["n"]))
    best_e = max(rows, key=lambda r: abs(r["delta_economic_per_fill"]))
    grades["Economic"] = _grade_economic(abs(best_e["delta_economic_per_fill"]), int(best_e["n"]))
    return rows, grades


def main() -> int:
    ap = argparse.ArgumentParser(description="Prefill Adverse-Selection Attribution v0.1")
    ap.add_argument("--dir", default=str(ROOT / "logs" / "maker_edge"))
    ap.add_argument("--venue-trades", default=str(ROOT / "logs" / "maker_edge" / "venue_trades.json"))
    ap.add_argument("--out", default=str(ROOT / "logs" / "maker_edge" / "Prefill_Adverse_Selection_Attribution_v0_1.txt"))
    ap.add_argument("--margin-sec", type=float, default=0.25)
    args = ap.parse_args()

    log_dir = Path(args.dir)
    df = _load_jsonl_df(log_dir)
    fills = df[df["event"] == "fill"].copy()
    paths = df[df["event"] == "fill_path"].copy()
    state_ticks = df[df["event"].isin(["mid_tick", "inventory_tick"])].copy()

    venue_trades = json.loads(Path(args.venue_trades).read_text())
    local_fills_raw = load_local_fills(log_dir)
    locals_norm = [normalize_local(e, i) for i, e in enumerate(local_fills_raw)]
    venues_norm = [normalize_venue(t, i) for i, t in enumerate(venue_trades)]
    recon = match(locals_norm, venues_norm)
    matched_fill_ids = {m["local"]["fill_id"] for m in recon["matched"]}
    matched_trade_ids = {m["venue"]["venue_trade_id"] for m in recon["matched"]}

    fills = fills[fills["fill_id"].isin(matched_fill_ids)].copy()
    paths = paths[paths["fill_id"].isin(matched_fill_ids)].copy()

    # merge labels/path info
    fill_meta_cols = [
        c
        for c in [
            "fill_id",
            "side",
            "fill_price",
            "amount",
            "quote_fill_time",
            "ts_epoch",
            "event_cluster_id",
            "pair",
        ]
        if c in fills.columns
    ]
    meta = fills.drop_duplicates("fill_id")[fill_meta_cols]
    paths = paths.merge(meta, on="fill_id", how="left", suffixes=("", "_f"))
    for col in ["side", "fill_price", "amount", "event_cluster_id", "quote_fill_time", "ts_epoch"]:
        alt = f"{col}_f"
        if alt in paths.columns:
            if col not in paths.columns:
                paths[col] = paths[alt]
            else:
                paths[col] = paths[col].fillna(paths[alt])
    paths["fill_ts"] = pd.to_datetime(paths["quote_fill_time"], utc=True, errors="coerce")
    # Prefer fill-event epoch seconds. astype(int64)/1e9 breaks when pandas stores UTC as us.
    fill_epoch = pd.to_numeric(paths["ts_epoch"], errors="coerce")
    iso_epoch = paths["fill_ts"].map(lambda ts: ts.timestamp() if pd.notna(ts) else np.nan)
    paths["fill_ts_epoch"] = fill_epoch.fillna(iso_epoch)
    paths["qty"] = pd.to_numeric(paths["amount"], errors="coerce")
    paths["fill_price"] = pd.to_numeric(paths["fill_price"], errors="coerce")
    paths["after_10s_price"] = pd.to_numeric(paths["after_10s_price"], errors="coerce")
    paths["after_30s_price"] = pd.to_numeric(paths["after_30s_price"], errors="coerce")
    paths["notional_usdt"] = paths["qty"] * paths["fill_price"]
    paths["markout_10s"] = _fav_ret(paths["side"], paths["fill_price"], paths["after_10s_price"])
    paths["markout_30s"] = _fav_ret(paths["side"], paths["fill_price"], paths["after_30s_price"])
    paths["path_c"] = paths["path_type"].astype(str).eq("C_toxic")
    paths["toxic"] = (paths["markout_10s"] < 0) & (paths["markout_30s"] < 0)
    paths["negative_30s"] = paths["markout_30s"] < 0

    # attach trade economics
    raw_v = pd.DataFrame(venue_trades)
    raw_v["trade_id_link"] = raw_v["id"].astype(str)
    raw_v["commission_usdt"] = pd.to_numeric(raw_v["commission"], errors="coerce")
    raw_v["realized_pnl_usdt"] = pd.to_numeric(raw_v["realizedPnl"], errors="coerce").fillna(0.0)
    matched_map = pd.DataFrame(
        [
            {
                "fill_id": m["local"]["fill_id"],
                "trade_id_link": m["venue"]["venue_trade_id"],
            }
            for m in recon["matched"]
        ]
    )
    paths = paths.merge(
        matched_map.merge(raw_v[["trade_id_link", "commission_usdt", "realized_pnl_usdt"]], on="trade_id_link", how="left"),
        on="fill_id",
        how="left",
    )
    paths["gross_markout_30s_usdt"] = paths["notional_usdt"] * paths["markout_30s"]
    paths["net_attr_30s_usdt"] = (
        paths["gross_markout_30s_usdt"]
        - pd.to_numeric(paths["commission_usdt"], errors="coerce").fillna(0.0)
        + pd.to_numeric(paths["realized_pnl_usdt"], errors="coerce").fillna(0.0)
    )
    paths["economic_negative"] = paths["net_attr_30s_usdt"] < 0

    # strict prefill state from sampled historical ticks only
    state_ticks = state_ticks.copy()
    state_ticks["ts_epoch"] = pd.to_numeric(state_ticks["ts_epoch"], errors="coerce")
    state_ticks = state_ticks.dropna(subset=["ts_epoch"]).sort_values("ts_epoch").drop_duplicates("ts_epoch")
    keep_cols = [
        c
        for c in [
            "ts_epoch",
            "mid",
            "spread",
            "bid_depth_1",
            "ask_depth_1",
            "bid_depth_5",
            "ask_depth_5",
            "obi",
            "delta",
            "trade_imbalance",
            "delta_efficiency",
            "inventory",
            "inventory_time",
            "inventory_skew",
        ]
        if c in state_ticks.columns
    ]
    states = state_ticks[keep_cols].copy()
    num_cols = [c for c in keep_cols if c != "ts_epoch"]
    for col in num_cols:
        states[col] = pd.to_numeric(states[col], errors="coerce")

    # 5s lag features using sampled states
    lag_df = states[["ts_epoch"] + [c for c in ["mid", "spread", "obi", "bid_depth_5", "ask_depth_5", "trade_imbalance", "delta"] if c in states.columns]].copy()
    lag_df["lag_ts"] = lag_df["ts_epoch"] + 5.0
    lag_cols = {c: f"{c}_past5s" for c in lag_df.columns if c not in {"ts_epoch", "lag_ts"}}
    lag_df = lag_df.rename(columns=lag_cols)

    paths = paths[paths["fill_ts_epoch"].notna()].copy()
    fill_states = paths[["fill_id", "fill_ts_epoch", "side"]].copy().sort_values("fill_ts_epoch")
    fill_states["feature_cutoff_ts"] = fill_states["fill_ts_epoch"] - float(args.margin_sec)

    # latest sampled tick strictly before fill-margin
    snap = pd.merge_asof(
        fill_states.sort_values("feature_cutoff_ts"),
        states.sort_values("ts_epoch"),
        left_on="feature_cutoff_ts",
        right_on="ts_epoch",
        direction="backward",
    )
    snap = snap[snap["ts_epoch"].notna()].copy()
    snap = pd.merge_asof(
        snap.sort_values("ts_epoch"),
        lag_df.sort_values("lag_ts"),
        left_on="ts_epoch",
        right_on="lag_ts",
        direction="backward",
    )
    if "ts_epoch_x" in snap.columns:
        snap = snap.rename(columns={"ts_epoch_x": "ts_epoch"})

    # derived strict-prefill features
    snap["spread_pct"] = snap["spread"] / snap["mid"]
    snap["depth_total_5"] = snap["bid_depth_5"] + snap["ask_depth_5"]
    snap["depth_imbalance_5"] = (snap["bid_depth_5"] - snap["ask_depth_5"]) / snap["depth_total_5"]
    snap["price_velocity_5s"] = (snap["mid"] - snap["mid_past5s"]) / snap["mid_past5s"]
    snap["spread_change_5s"] = snap["spread_pct"] - (snap["spread_past5s"] / snap["mid_past5s"])
    snap["obi_change_5s"] = snap["obi"] - snap["obi_past5s"]
    snap["depth_total_5_past"] = snap["bid_depth_5_past5s"] + snap["ask_depth_5_past5s"]
    snap["depth_change_5s"] = snap["depth_total_5"] - snap["depth_total_5_past"]
    snap["trade_imbalance_change_5s"] = snap["trade_imbalance"] - snap["trade_imbalance_past5s"]
    snap["delta_change_5s"] = snap["delta"] - snap["delta_past5s"]
    snap["pre_deteriorated_strict"] = np.where(
        snap["side"].eq("long"),
        (snap["price_velocity_5s"] < 0) | (snap["depth_change_5s"] < 0),
        (snap["price_velocity_5s"] > 0) | (snap["depth_change_5s"] < 0),
    )
    snap["feature_age_ms"] = (snap["fill_ts_epoch"] - snap["ts_epoch"]) * 1000.0
    snap = snap.rename(columns={"ts_epoch": "feature_ts_epoch"})

    snap_feature_cols = [
        "fill_id",
        "feature_ts_epoch",
        "feature_cutoff_ts",
        "mid",
        "spread",
        "bid_depth_1",
        "ask_depth_1",
        "bid_depth_5",
        "ask_depth_5",
        "obi",
        "delta",
        "trade_imbalance",
        "delta_efficiency",
        "inventory",
        "inventory_time",
        "inventory_skew",
        "mid_past5s",
        "spread_past5s",
        "obi_past5s",
        "bid_depth_5_past5s",
        "ask_depth_5_past5s",
        "trade_imbalance_past5s",
        "delta_past5s",
        "spread_pct",
        "depth_total_5",
        "depth_imbalance_5",
        "price_velocity_5s",
        "spread_change_5s",
        "depth_total_5_past",
        "depth_change_5s",
        "obi_change_5s",
        "trade_imbalance_change_5s",
        "delta_change_5s",
        "pre_deteriorated_strict",
        "feature_age_ms",
    ]
    snap_feature_cols = [c for c in snap_feature_cols if c in snap.columns]
    rename_map = {
        c: f"strict_{c}"
        for c in snap_feature_cols
        if c not in {"fill_id", "feature_ts_epoch", "feature_cutoff_ts", "feature_age_ms", "pre_deteriorated_strict"}
    }
    rename_map["feature_ts_epoch"] = "strict_feature_ts_epoch"
    rename_map["feature_cutoff_ts"] = "strict_feature_cutoff_ts"
    rename_map["feature_age_ms"] = "strict_feature_age_ms"
    rename_map["pre_deteriorated_strict"] = "strict_pre_deteriorated"
    snap_merge = snap[snap_feature_cols].rename(columns=rename_map)
    pref = paths.merge(snap_merge, on="fill_id", how="left")
    pref = pref[pref["strict_feature_ts_epoch"].notna()].copy()

    labels = ["path_c", "toxic", "negative_30s"]
    numeric_features = [
        "strict_obi",
        "strict_delta",
        "strict_trade_imbalance",
        "strict_spread_pct",
        "strict_bid_depth_5",
        "strict_ask_depth_5",
        "strict_depth_total_5",
        "strict_depth_imbalance_5",
        "strict_price_velocity_5s",
        "strict_spread_change_5s",
        "strict_depth_change_5s",
        "strict_obi_change_5s",
        "strict_trade_imbalance_change_5s",
        "strict_delta_change_5s",
        "strict_inventory",
        "strict_inventory_skew",
        "strict_inventory_time",
        "strict_feature_age_ms",
    ]
    cat_features = ["strict_pre_deteriorated"]

    result_rows: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []
    for feat in numeric_features:
        if feat not in pref.columns:
            continue
        rows, grades = _state_table_num(pref, feat, labels)
        result_rows.extend(rows)
        matrix_rows.append(
            {
                "feature": feat,
                "Path C": grades["path_c"],
                "Toxic": grades["toxic"],
                "Neg30s": grades["negative_30s"],
                "Economic": grades["Economic"],
            }
        )
    for feat in cat_features:
        if feat not in pref.columns:
            continue
        rows, grades = _state_table_cat(pref, feat, labels)
        result_rows.extend(rows)
        matrix_rows.append(
            {
                "feature": feat,
                "Path C": grades["path_c"],
                "Toxic": grades["toxic"],
                "Neg30s": grades["negative_30s"],
                "Economic": grades["Economic"],
            }
        )

    baseline = {
        "path_c": float(pref["path_c"].mean()),
        "toxic": float(pref["toxic"].mean()),
        "negative_30s": float(pref["negative_30s"].mean()),
        "economic_negative": float(pref["economic_negative"].mean()),
        "net_attr_30s_usdt_mean": float(pref["net_attr_30s_usdt"].mean()),
        "markout_30s_mean": float(pref["markout_30s"].mean()),
    }
    coverage = {
        "matched_paths": int(len(paths)),
        "strict_prefill_rows": int(len(pref)),
        "strict_prefill_coverage_pct": float(len(pref) / max(len(paths), 1) * 100.0),
        "mean_feature_age_ms": float(pref["strict_feature_age_ms"].mean()),
        "median_feature_age_ms": float(pref["strict_feature_age_ms"].median()),
    }

    out_txt = Path(args.out)
    out_json = out_txt.with_suffix(".json")
    lines: list[str] = []

    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    p("=" * 72)
    p("Prefill Adverse-Selection Attribution v0.1")
    p("=" * 72)
    p("Experiment: MM_EDGE_EXP_001")
    p("Population: frozen historical fills (Hard core = MATCHED only)")
    p("Strategy: v0.1 FROZEN")
    p("Execution: STOPPED")
    p("Purpose: Pre-fill adverse-selection predictability audit")
    p("NOT: strategy / backtest / optimization / model training")
    p()
    p("Time Contract")
    p("-" * 40)
    p(f"feature_timestamp <= t_fill - {args.margin_sec:.2f}s")
    p("Only sampled historical mid_tick / inventory_tick states are used.")
    p("Fill-callback contemporaneous fields are intentionally excluded to avoid leakage.")
    p()
    p("Unavailable under strict contract in v0.1")
    p("-" * 40)
    p("- event intensity / large trades / time_since_last_market_event")
    p("- fill-callback market_event_before_fill")
    p("- any future path / realized / cancel-after-fill info as features")
    p()
    p("Baseline labels (MATCHED only)")
    p("-" * 40)
    p(f"P(Path C):             {_pct(baseline['path_c'])}")
    p(f"P(Toxic):              {_pct(baseline['toxic'])}")
    p(f"P(Neg30s):             {_pct(baseline['negative_30s'])}")
    p(f"P(Economic<0):         {_pct(baseline['economic_negative'])}")
    p(f"Mean net_attr_30s:     {_num(baseline['net_attr_30s_usdt_mean'], 6)} USDT/fill")
    p(f"Mean markout_30s:      {_pct(baseline['markout_30s_mean'])}")
    p(f"Matched path rows:     {coverage['matched_paths']}")
    p(f"Strict prefill rows:   {coverage['strict_prefill_rows']}")
    p(f"Strict coverage:       {coverage['strict_prefill_coverage_pct']:.1f}%")
    p(f"Feature age ms:        mean={coverage['mean_feature_age_ms']:.1f} median={coverage['median_feature_age_ms']:.1f}")
    p()
    p("Sample-size policy")
    p("-" * 40)
    p("n < 30   exploratory only (LOW_N)")
    p("n < 100  weak evidence (WEAK_EVIDENCE)")
    p("n >= 100 usable attribution (USABLE)")
    p()
    p("Conclusion Matrix")
    p("-" * 40)
    p("feature | Path C | Toxic | Neg30s | Economic")
    for row in matrix_rows:
        p(f"{row['feature']} | {row['Path C']} | {row['Toxic']} | {row['Neg30s']} | {row['Economic']}")
    p()
    p("State tables")
    p("-" * 40)
    for feat in [r["feature"] for r in matrix_rows]:
        sub = [r for r in result_rows if r["feature"] == feat]
        if not sub:
            continue
        p(feat)
        for r in sub:
            med = _num(r["median"], 6) if r["median"] is not None else "n/a"
            p(
                f"  {r['state']}: n={r['n']} [{r['sample_grade']}] median={med} "
                f"P(C)={_pct(r['p_path_c'])} Δ={r['delta_path_c_pp']:+.1f}pp "
                f"P(Toxic)={_pct(r['p_toxic'])} Δ={r['delta_toxic_pp']:+.1f}pp "
                f"P(Neg30)={_pct(r['p_negative_30s'])} Δ={r['delta_negative_30s_pp']:+.1f}pp "
                f"E[net30]={_num(r['net_attr_mean'], 5)} Δ={_num(r['delta_economic_per_fill'], 5)}"
            )
        p()
    p("Interpretation")
    p("-" * 40)
    p("Only pre-fill observable states count as candidate signals.")
    p("A feature may separate Path C statistically but still fail Economic relevance.")
    p("Only rows graded CANDIDATE_V0_2_SIGNAL with usable n should enter v0.2 hypothesis design.")
    p("=" * 72)

    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(
        json.dumps(
            {
                "experiment_id": "MM_EDGE_EXP_001",
                "purpose": "prefill adverse-selection predictability audit",
                "population": {
                    "matched_rows": int(len(pref)),
                    "margin_sec": float(args.margin_sec),
                },
                "baseline": baseline,
                "coverage": coverage,
                "matrix": matrix_rows,
                "states": result_rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

