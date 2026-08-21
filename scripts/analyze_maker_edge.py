#!/usr/bin/env python3
"""
Maker Edge Report v0.1 — Research Freeze / Data Collection Phase

固定格式（每次运行必须相同、可比较）：
  Executive Summary
  Section 1 — Data Integrity
  Section 2 — Fill Alpha
  Section 3 — Toxicity Profile
  Section 4 — Observed Edge Attribution
  Section 5 — Decision

研究对象：可验证的市场现象（不是策略）。
见 FREEZE.md — 只许数据字段/质量检查/报告解释；禁止新交易规则。

用法：
  ./scripts/analyze.sh 2000
  python scripts/analyze_maker_edge.py --report --min-fills 2000
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


FEE = 0.00016
EXPECTED_SLIPPAGE = 0.00005
POSITIVE_EDGE_NET = 0.0002
CLUSTER_GAP_SEC = 30.0
TOXIC_FAIL_RATIO = 0.60
PASS_MIN_FILLS_DEFAULT = 2000


def _load_experiment_from_df(df: pd.DataFrame) -> dict[str, Any]:
    """优先用 jsonl 中的 experiment_start / 事件戳；否则回退环境默认。"""
    try:
        from nautilus_mm.experiment import load_experiment_meta

        base = load_experiment_meta()
    except Exception:
        base = {
            "experiment_id": "MM_EDGE_EXP_001",
            "probe_version": "probe_v0.1",
            "quote_assumption": "frozen",
            "fee_model": "frozen",
            "exchange_assumption": "frozen",
            "exchange": "binance_usdm",
            "environment": "TESTNET",
            "symbol": "BTCUSDT-PERP",
        }
    if df.empty or "event" not in df.columns:
        return base
    starts = df[df["event"] == "experiment_start"]
    if not starts.empty:
        row = starts.iloc[-1]
        for k in ("experiment_id", "probe_version", "exchange", "environment", "symbol"):
            if k in row and pd.notna(row[k]):
                base[k] = row[k]
        return base
    # 任意带 experiment_id 的事件
    if "experiment_id" in df.columns and df["experiment_id"].notna().any():
        base["experiment_id"] = df["experiment_id"].dropna().iloc[-1]
    if "probe_version" in df.columns and df["probe_version"].notna().any():
        base["probe_version"] = df["probe_version"].dropna().iloc[-1]
    return base


def load_events(log_dir: Path) -> pd.DataFrame:
    rows = []
    files = sorted(log_dir.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No jsonl in {log_dir}")
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


def _fav_ret(side: pd.Series, fill: pd.Series, px: pd.Series) -> pd.Series:
    raw = (px.astype(float) - fill.astype(float)) / fill.astype(float)
    return pd.Series(np.where(side == "long", raw, -raw), index=side.index)


def _side_label(side: str) -> str:
    return "Bid" if side == "long" else "Ask"


def _extract_fill_context(fills: pd.DataFrame) -> pd.DataFrame:
    if fills.empty or "fill_context" not in fills.columns:
        return pd.DataFrame()
    rows = []
    for _, r in fills.iterrows():
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


def _median_safe(s: pd.Series) -> float | None:
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(s.median()) if len(s) else None


def _fmt_pct(x: float | None, digits: int = 4) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{x*100:+.{digits}f}%"


def _fmt_pp(x: float | None) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{x*100:+.1f}pp"


def _dist_stats(s: pd.Series) -> dict[str, float | None]:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"mean": None, "median": None, "p25": None, "p75": None, "n": 0}
    return {
        "mean": float(s.mean()),
        "median": float(s.median()),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
        "n": int(len(s)),
    }


def _print_dist(p, title: str, d: dict[str, float | None]) -> None:
    if not d.get("n"):
        p(f"{title}: n/a")
        return
    p(f"{title} (n={d['n']}):")
    p(f"  mean:   {_fmt_pct(d['mean'])}")
    p(f"  median: {_fmt_pct(d['median'])}")
    p(f"  p25:    {_fmt_pct(d['p25'])}")
    p(f"  p75:    {_fmt_pct(d['p75'])}")


def _observation_window(n_fills: int, n_clusters: int) -> str:
    if n_fills < 500:
        return "anomaly-check only (<500 fills)"
    if n_fills < 2000:
        return "early look (500+) — do not over-interpret"
    if n_fills < 10000:
        return "preliminary judgment (2000+) — clusters still matter more than fills"
    return "stability discussion eligible (10000+ fills)"


def assign_clusters_offline(fills: pd.DataFrame, gap_sec: float = CLUSTER_GAP_SEC) -> pd.DataFrame:
    out = fills.copy()
    if out.empty:
        return out
    if "event_cluster_id" in out.columns and out["event_cluster_id"].notna().any():
        return out
    if "ts_epoch" not in out.columns:
        out["event_cluster_id"] = [f"na_{i}" for i in range(len(out))]
        out["cluster_fill_index"] = 1
        return out
    out = out.sort_values("ts_epoch").reset_index(drop=True)
    cids: list[str] = []
    idxs: list[int] = []
    cid = None
    last_ts = -1e18
    last_side = None
    n = 0
    for _, r in out.iterrows():
        ts = float(r["ts_epoch"])
        side = r.get("side")
        if cid is None or side != last_side or (ts - last_ts) > gap_sec:
            cid = uuid.uuid4().hex[:12]
            n = 0
        n += 1
        cids.append(cid)
        idxs.append(n)
        last_ts = ts
        last_side = side
    out["event_cluster_id"] = cids
    out["cluster_fill_index"] = idxs
    return out


def classify_space(raw_capture: float, net_edge: float) -> str:
    if raw_capture <= 0 or net_edge <= 0:
        return "NO_EDGE"
    if net_edge < POSITIVE_EDGE_NET:
        return "EDGE_AFTER_COST"
    return "POSITIVE_EDGE"


def build_mid_series(df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for ev in ("mid_tick", "inventory_tick"):
        if "event" not in df.columns:
            break
        sub = df[df["event"] == ev]
        if sub.empty or "mid" not in sub.columns or "ts_epoch" not in sub.columns:
            continue
        parts.append(sub[["ts_epoch", "mid"]].dropna())
    if not parts:
        return pd.DataFrame(columns=["ts_epoch", "mid"])
    m = pd.concat(parts, ignore_index=True)
    m["ts_epoch"] = pd.to_numeric(m["ts_epoch"], errors="coerce")
    m["mid"] = pd.to_numeric(m["mid"], errors="coerce")
    return m.dropna().sort_values("ts_epoch").drop_duplicates("ts_epoch").reset_index(drop=True)


def _cluster_weight(frame: pd.DataFrame) -> pd.Series:
    if "event_cluster_id" not in frame.columns:
        return pd.Series(1.0, index=frame.index)
    cnt = frame.groupby("event_cluster_id")["event_cluster_id"].transform("count")
    return 1.0 / cnt.clip(lower=1)


def _period_str(df: pd.DataFrame) -> str:
    if df.empty or "ts_epoch" not in df.columns or df["ts_epoch"].isna().all():
        return "n/a"
    t0 = float(pd.to_numeric(df["ts_epoch"], errors="coerce").min())
    t1 = float(pd.to_numeric(df["ts_epoch"], errors="coerce").max())
    a = datetime.fromtimestamp(t0, tz=timezone.utc).strftime("%Y-%m-%d")
    b = datetime.fromtimestamp(t1, tz=timezone.utc).strftime("%Y-%m-%d")
    return f"{a} ~ {b}"


def _instrument(fills: pd.DataFrame, df: pd.DataFrame) -> str:
    for src in (fills, df):
        if not src.empty and "pair" in src.columns and src["pair"].notna().any():
            return str(src["pair"].dropna().iloc[0])
    return "BTCUSDT Perpetual (assumed)"


def _maker_alpha_frame(g: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return (fill_ret, mkt_signed) for MakerAlpha = fill − market."""
    mid0 = g["mid"].astype(float)
    mid1 = g["after_30s_price"].astype(float)
    mkt_ret = (mid1 - mid0) / mid0
    mkt_signed = pd.Series(
        np.where(g["side"] == "long", mkt_ret, -mkt_ret), index=g.index
    )
    fill_ret = _fav_ret(g["side"], g["fill_price"], g["after_30s_price"])
    return fill_ret, mkt_signed


def report(df: pd.DataFrame, min_fills: int = PASS_MIN_FILLS_DEFAULT, out_path: Path | None = None) -> dict[str, Any]:
    fills = df[df["event"] == "fill"].copy() if "event" in df.columns else pd.DataFrame()
    paths = df[df["event"] == "fill_path"].copy() if "event" in df.columns else pd.DataFrame()
    health = df[df["event"] == "health"].copy() if "event" in df.columns else pd.DataFrame()
    exp = _load_experiment_from_df(df)

    lines: list[str] = []

    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    if not fills.empty:
        fills = assign_clusters_offline(fills)

    if not paths.empty and not fills.empty and "fill_id" in fills.columns:
        meta_cols = [
            c
            for c in [
                "side",
                "fill_price",
                "fill_reason",
                "spread",
                "spread_capture_pct",
                "obi",
                "trade_imbalance",
                "bid_depth_5",
                "ask_depth_5",
                "book_age_ms",
                "inventory",
                "pre_5s_deteriorated",
                "mid",
                "event_cluster_id",
                "cluster_fill_index",
                "ts_epoch",
                "pair",
            ]
            if c in fills.columns
        ]
        meta = fills.drop_duplicates("fill_id")[["fill_id"] + meta_cols]
        paths = paths.merge(meta, on="fill_id", how="left", suffixes=("", "_f"))
        for col in ("side", "fill_price", "mid", "event_cluster_id", "spread", "spread_capture_pct"):
            alt = f"{col}_f"
            if alt in paths.columns:
                if col not in paths.columns:
                    paths[col] = paths[alt]
                else:
                    paths[col] = paths[col].fillna(paths[alt])
        fc = _extract_fill_context(fills)
        if not fc.empty:
            paths = paths.merge(fc, on="fill_id", how="left")

    n_fills = len(fills)
    n_paths = len(paths)
    n_clusters = int(fills["event_cluster_id"].nunique()) if n_fills and "event_cluster_id" in fills.columns else 0
    cluster_fill_ratio = n_clusters / max(n_fills, 1)

    # ---------- compute: integrity ----------
    integrity_ok = True
    integrity_notes: list[str] = []
    healthy_ratio = gap_total = gap_win_max = None
    lat_p50 = lat_p95 = lat_p99 = ba_med = None
    if health.empty:
        integrity_ok = False
        integrity_notes.append("no health telemetry")
    else:
        healthy_ratio = float(health["healthy"].astype(bool).mean()) if "healthy" in health.columns else 0.0
        gap_total = int(health["sequence_gap"].iloc[-1]) if "sequence_gap" in health.columns else 0
        gap_win_max = (
            int(pd.to_numeric(health.get("sequence_gap_window"), errors="coerce").fillna(0).max())
            if "sequence_gap_window" in health.columns
            else 0
        )
        lat_p50 = health["latency_ms_p50"].iloc[-1] if "latency_ms_p50" in health.columns else None
        lat_p95 = health["latency_ms_p95"].iloc[-1] if "latency_ms_p95" in health.columns else None
        lat_p99 = health["latency_ms_p99"].iloc[-1] if "latency_ms_p99" in health.columns else None
        ba_series = (
            fills["book_age_ms"]
            if "book_age_ms" in fills.columns and fills["book_age_ms"].notna().any()
            else health.get("book_age_ms")
        )
        ba_med = _median_safe(ba_series) if ba_series is not None else None
        if healthy_ratio < 0.99:
            integrity_ok = False
            integrity_notes.append(f"healthy_ratio={healthy_ratio*100:.2f}% < 99%")
        # Binance depth update ids are not contiguous — log only, do not INVALID.
        if gap_win_max and gap_win_max > 0:
            integrity_notes.append(
                f"sequence_gap_window_max={gap_win_max} (observe-only; Binance ids skip)"
            )
        if ba_med is not None and ba_med > 500:
            integrity_ok = False
            integrity_notes.append(f"book_age_median={ba_med:.0f}ms > 500ms")

    decision: dict[str, Any] = {
        "integrity": integrity_ok,
        "verdict": "INSUFFICIENT_DATA",
        "reasons": [],
        "space_class": None,
        "benchmark_alpha": None,
        "maker_alpha_mean": None,
        "quality": {
            "fills": n_fills,
            "clusters": n_clusters,
            "cluster_fill_ratio": cluster_fill_ratio,
            "healthy_ratio": healthy_ratio,
        },
    }

    if fills.empty:
        p("=" * 72)
        p("Maker Edge Report v0.1")
        p("Phase: Research Freeze / Data Collection")
        p("=" * 72)
        p("\nExecutive Summary")
        p(f"  Experiment: {exp.get('experiment_id')}")
        p(f"  Version:    {exp.get('probe_version')}")
        p("  Quote:      frozen")
        p("  Fee:        frozen")
        p("  Exchange:   frozen")
        p(f"  Period:     {_period_str(df)}")
        p(f"  Instrument: {_instrument(fills, df)}")
        p("  Samples:")
        p("    fills:    0")
        p("    clusters: 0")
        p("  Decision:  INSUFFICIENT_DATA")
        p("  Reason:    no fills yet — run probe")
        decision["experiment"] = exp
        _finish(lines, out_path, decision)
        return decision

    # ---------- compute: fill alpha table + distributions ----------
    alpha_table: dict[str, dict[str, float | None]] = {
        "Bid": {"fill_w": None, "cluster_w": None},
        "Ask": {"fill_w": None, "cluster_w": None},
        "Overall": {"fill_w": None, "cluster_w": None},
    }
    fill_alpha_dist: dict[str, float | None] = {}
    cluster_alpha_dist: dict[str, float | None] = {}
    fq_pass = None
    bench_alpha = None
    maker_alpha_mean = None
    agree = None
    pct_fills_positive_alpha = None

    if not paths.empty and "after_30s_price" in paths.columns and "mid" in paths.columns and paths["mid"].notna().any():
        for side_name, g in paths.groupby("side"):
            label = _side_label(str(side_name))
            fill_ret, mkt_signed = _maker_alpha_frame(g)
            alpha = fill_ret - mkt_signed
            w = _cluster_weight(g)
            alpha_table[label]["fill_w"] = float(alpha.mean())
            alpha_table[label]["cluster_w"] = float((alpha * w).sum() / w.sum()) if w.sum() else float(alpha.mean())

        fill_ret, mkt_signed = _maker_alpha_frame(paths)
        alpha = fill_ret - mkt_signed
        w = _cluster_weight(paths)
        alpha_table["Overall"]["fill_w"] = float(alpha.mean())
        alpha_table["Overall"]["cluster_w"] = (
            float((alpha * w).sum() / w.sum()) if w.sum() else float(alpha.mean())
        )
        maker_alpha_mean = alpha_table["Overall"]["cluster_w"]
        fw, cw = alpha_table["Overall"]["fill_w"], alpha_table["Overall"]["cluster_w"]
        agree = (fw > 0 and cw > 0) or (fw <= 0 and cw <= 0)
        fill_alpha_dist = _dist_stats(alpha)
        pct_fills_positive_alpha = float((alpha > 0).mean())

        # per-cluster mean MakerAlpha（事件级分布）
        if "event_cluster_id" in paths.columns:
            tmp = paths.assign(_alpha=alpha)
            cluster_means = tmp.groupby("event_cluster_id")["_alpha"].mean()
            cluster_alpha_dist = _dist_stats(cluster_means)

        mkt_fav = mkt_signed > 0
        fill_fav = fill_ret > 0
        bench_alpha = float(np.mean(fill_fav) - np.mean(mkt_fav))

        fav30 = fill_ret
        p30_clu = float((fav30 > 0).astype(float).mul(w).sum() / w.sum()) if w.sum() else float((fav30 > 0).mean())
        fq_pass = p30_clu > 0.50

    decision["fill_quality"] = fq_pass
    decision["benchmark_alpha"] = bench_alpha
    decision["maker_alpha_mean"] = maker_alpha_mean

    # ---------- compute: toxicity + loss concentration ----------
    toxicity: dict[str, dict[str, float | None]] = {}
    toxic_bid_ratio = None
    c_share = None
    tox_dist: dict[str, Any] = {}
    if not paths.empty:
        for side_name, g in paths.groupby("side"):
            label = _side_label(str(side_name))
            row: dict[str, float | None] = {}
            for hz, col in [
                ("1s", "after_1s_price"),
                ("5s", "after_5s_price"),
                ("10s", "after_10s_price"),
                ("30s", "after_30s_price"),
                ("300s", "after_5m_price"),
            ]:
                if col in g.columns:
                    row[hz] = float(_fav_ret(g["side"], g["fill_price"], g[col]).mean())
                else:
                    row[hz] = None
            toxicity[label] = row
        if "path_type" in paths.columns:
            c_share = float((paths["path_type"].astype(str).str.startswith("C")).mean())
            bid = paths[paths["side"] == "long"]
            if len(bid):
                toxic_bid_ratio = float((bid["path_type"].astype(str).str.startswith("C")).mean())

        # 毒性分布：多少成交在 10s 不利；最差 20% 占总不利损失比例
        if "after_10s_price" in paths.columns:
            fav10 = _fav_ret(paths["side"], paths["fill_price"], paths["after_10s_price"])
            adverse = fav10[fav10 < 0]
            tox_dist["pct_adverse_10s"] = float((fav10 < 0).mean())
            tox_dist["fav10"] = _dist_stats(fav10)
            if len(adverse) >= 5:
                worst_n = max(1, int(np.ceil(0.20 * len(fav10))))
                worst = fav10.nsmallest(worst_n)
                total_adv = float((-adverse).sum())
                worst_adv = float((-worst.clip(upper=0)).sum())
                tox_dist["worst20_share_of_adverse"] = (
                    worst_adv / total_adv if total_adv > 1e-12 else None
                )
            else:
                tox_dist["worst20_share_of_adverse"] = None

    # ---------- compute: cost / adverse ----------
    space_class = None
    adv_pass = None
    raw_capture = net_edge = adv_mag = sc_mean = total_cost = None
    if not paths.empty and "after_30s_price" in paths.columns:
        fav30 = _fav_ret(paths["side"], paths["fill_price"], paths["after_30s_price"])
        w = _cluster_weight(paths)
        raw_capture = float((fav30 * w).sum() / w.sum()) if w.sum() else float(fav30.mean())
        adv_mag = (
            float((-fav30.clip(upper=0) * w).sum() / w.sum())
            if w.sum()
            else float((-fav30.clip(upper=0)).mean())
        )
        sc_mean = (
            float(fills["spread_capture_pct"].mean())
            if "spread_capture_pct" in fills.columns and fills["spread_capture_pct"].notna().any()
            else 0.0
        )
        if "book_age_ms" in fills.columns and fills["book_age_ms"].notna().any():
            latency_cost = float(fills["book_age_ms"].mean()) / 100.0 * 0.00002
        else:
            latency_cost = 0.00002
        total_cost = 2 * FEE + EXPECTED_SLIPPAGE + latency_cost
        net_edge = raw_capture - total_cost
        space_class = classify_space(raw_capture, net_edge)
        adv_ok = (adv_mag < abs(sc_mean)) if sc_mean != 0 else False
        adv_pass = bool(adv_ok and space_class in ("POSITIVE_EDGE", "EDGE_AFTER_COST"))

    decision["adverse"] = adv_pass
    decision["space_class"] = space_class

    # ---------- compute: attribution (facts only) ----------
    attr_rows: list[tuple[str, str, int, float]] = []
    stab_pass = None
    state_coverage_ok = None
    concentrated = False
    positive_envs = 0
    total_envs = 0
    if not paths.empty and "after_30s_price" in paths.columns:
        paths = paths.copy()
        paths["_fav30"] = _fav_ret(paths["side"], paths["fill_price"], paths["after_30s_price"])
        if "vol_proxy_5m" in paths.columns and paths["vol_proxy_5m"].notna().any():
            med = paths["vol_proxy_5m"].median()
            paths["vol_bucket"] = np.where(paths["vol_proxy_5m"] >= med, "high_vol", "low_vol")
        elif "max_price" in paths.columns:
            rng = (paths["max_price"] - paths["min_price"]) / paths["fill_price"]
            paths["vol_bucket"] = np.where(rng >= rng.median(), "high_vol", "low_vol")
        if "price_velocity_5s" in paths.columns and paths["price_velocity_5s"].notna().any():
            v = paths["price_velocity_5s"].astype(float)
            thr = v.abs().median() * 0.5
            paths["trend_bucket"] = np.where(
                v > thr, "trend_up", np.where(v < -thr, "trend_down", "range")
            )
        if "spread" in paths.columns and paths["spread"].notna().any():
            sp_pct = paths["spread"] / paths["fill_price"]
            paths["liq_bucket"] = np.where(sp_pct <= sp_pct.median(), "tight_spread", "wide_spread")
        if "bid_depth_5" in paths.columns and "ask_depth_5" in paths.columns:
            depth = paths["bid_depth_5"].fillna(0) + paths["ask_depth_5"].fillna(0)
            if depth.gt(0).any():
                paths["depth_bucket"] = np.where(depth >= depth[depth > 0].median(), "deep_book", "thin_book")

        pos_counts: list[int] = []
        for col, title in [
            ("vol_bucket", "Volatility"),
            ("trend_bucket", "Trend"),
            ("liq_bucket", "Liquidity(spread)"),
            ("depth_bucket", "Liquidity(depth)"),
            ("market_event_before_fill", "FillContext"),
            ("path_type", "PathType"),
        ]:
            if col not in paths.columns or paths[col].isna().all():
                continue
            for idx, row in paths.groupby(col)["_fav30"].agg(["count", "mean"]).iterrows():
                total_envs += 1
                mean = float(row["mean"])
                n = int(row["count"])
                attr_rows.append((title, str(idx), n, mean))
                if mean > 0:
                    positive_envs += 1
                    pos_counts.append(n)

        state_coverage_ok = total_envs >= 4
        if total_envs >= 2:
            if pos_counts:
                concentrated = (max(pos_counts) / max(sum(pos_counts), 1)) >= 0.70 and len(pos_counts) == 1
            stab_pass = positive_envs >= 2 and not concentrated
        else:
            state_coverage_ok = False

    decision["stability"] = stab_pass
    decision["quality"]["state_buckets"] = len(attr_rows)

    # ---------- decision ----------
    independence_ok = (
        n_clusters >= max(50, min_fills // 20) if n_fills >= min_fills else None
    )
    decision["independence"] = independence_ok
    reasons: list[str] = []

    min_paths = max(1, min_fills // 10)
    sample_ok = n_fills >= min_fills and n_paths >= min_paths

    gates = {
        "integrity": integrity_ok,
        "fill_quality": fq_pass,
        "adverse": adv_pass,
        "stability": stab_pass,
    }

    hard_fail = False
    if not integrity_ok:
        hard_fail = True
        reasons.append("data integrity failed — stop interpretation")
    if toxic_bid_ratio is not None and toxic_bid_ratio > TOXIC_FAIL_RATIO:
        hard_fail = True
        reasons.append(f"Bid toxic fill ratio {toxic_bid_ratio*100:.0f}% > {TOXIC_FAIL_RATIO*100:.0f}%")
    if space_class == "NO_EDGE" and sample_ok:
        hard_fail = True
        reasons.append("edge disappears after cost / NO_EDGE")
    if bench_alpha is not None and bench_alpha <= 0 and sample_ok:
        reasons.append("benchmark-adjusted alpha negative")
    if maker_alpha_mean is not None and maker_alpha_mean <= 0 and sample_ok:
        reasons.append("MakerAlpha (fill−market) ≤ 0")
    if adv_pass is False and sample_ok:
        reasons.append("adverse selection ≥ spread capture")
    if concentrated:
        reasons.append("edge concentrated in single regime")

    pass_extras = True
    if bench_alpha is not None and bench_alpha <= 0:
        pass_extras = False
    if independence_ok is False:
        pass_extras = False
        reasons.append(f"insufficient independent clusters ({n_clusters})")
    if space_class == "NO_EDGE":
        pass_extras = False

    all_gates = all(v is True for v in gates.values())

    # Stage3 unlock checklist（严格）
    stage3_unlock = {
        "data_integrity": integrity_ok is True,
        "cluster_weighted_alpha_gt_0": bool(maker_alpha_mean is not None and maker_alpha_mean > 0),
        "benchmark_alpha_gt_0": bool(bench_alpha is not None and bench_alpha > 0),
        "not_concentrated": not concentrated,
    }
    stage3_ready = all(stage3_unlock.values()) and sample_ok and all_gates and pass_extras

    # 局部正 edge：归因桶分化或集中在单一正 regime
    local_positive = positive_envs >= 1 and total_envs >= 2 and (
        (positive_envs < total_envs) or concentrated
    )

    if not integrity_ok:
        verdict = "INVALID"
        reasons = ["Data Integrity FAIL — do not interpret Alpha; discard / keep collecting clean data"]
        reasons.extend(integrity_notes)
    elif not sample_ok or state_coverage_ok is False:
        verdict = "COLLECTING"
        reasons = []
        if n_fills < min_fills:
            reasons.append(f"fills {n_fills} < {min_fills}")
        if n_paths < min_paths:
            reasons.append(f"fill_paths {n_paths} < {min_paths}")
        if n_clusters < max(50, min_fills // 20) and n_fills >= 500:
            reasons.append(f"clusters {n_clusters} insufficient (independent liquidity events)")
        if state_coverage_ok is False:
            reasons.append("state coverage incomplete")
        if not reasons:
            reasons.append("Insufficient independent liquidity events")
    elif hard_fail and not local_positive:
        verdict = "FAIL"
        if not reasons:
            reasons.append("market hypothesis does not hold under current quote assumption")
    elif stage3_ready:
        verdict = "PASS"
        reasons = [
            "Maker alpha survives: cost",
            "Maker alpha survives: benchmark",
            "Maker alpha survives: cluster weighting",
            "Maker alpha survives: multiple states",
        ]
    elif local_positive and integrity_ok and sample_ok:
        verdict = "PARTIAL_PASS"
        reasons = [
            "edge not universal — observed only in subset of states/events",
            f"positive attribution buckets: {positive_envs}/{total_envs}",
        ]
        if concentrated:
            reasons.append("edge concentrated in one regime/event class")
        if maker_alpha_mean is not None and maker_alpha_mean <= 0:
            reasons.append("overall cluster-weighted MakerAlpha ≤ 0")
    else:
        verdict = "FAIL"
        if not reasons:
            reasons.append("gates failed under current quote assumption")
        if adv_pass is False:
            reasons.insert(0, "adverse selection")
        if sc_mean is not None and abs(sc_mean) < 1e-8:
            reasons.append("insufficient spread")

    decision["verdict"] = verdict
    decision["reasons"] = reasons
    decision["stage3_unlock"] = stage3_unlock
    decision["stage3_ready"] = stage3_ready
    decision["experiment"] = exp

    # ==================================================================
    # PRINT — fixed format
    # ==================================================================
    p("=" * 72)
    p("Maker Edge Report v0.1")
    p("Phase: Research Freeze / Data Collection")
    p("Object: verifiable market phenomenon (not a strategy)")
    p("=" * 72)

    # ----- Executive Summary -----
    p("\nExecutive Summary")
    p("-" * 40)
    p(f"Experiment: {exp.get('experiment_id')}")
    p(f"Version:    {exp.get('probe_version')}")
    p("Quote:      frozen")
    p("Fee:        frozen")
    p("Exchange:   frozen")
    p(f"Venue:      {exp.get('exchange')} / {exp.get('environment')}")
    p(f"Period:     {_period_str(df if not df.empty else fills)}")
    p(f"Instrument: {_instrument(fills, df)}")
    p("Samples:")
    p(f"  fills:    {n_fills}")
    p(f"  clusters: {n_clusters}")
    p(f"  paths:    {n_paths}")
    p(f"  cluster/fill: {cluster_fill_ratio*100:.1f}%")
    p(f"Observation window: {_observation_window(n_fills, n_clusters)}")
    p("  (500=anomaly · 2000=preliminary · 10000=stability; clusters > fills)")
    p(f"Decision:   {verdict}")
    p("Reason:")
    for r in reasons:
        p(f"  - {r}")
    p("Hypothesis under test: passive fills produce +MakerAlpha")
    p("  under current BTC perp / venue / quote / execution — not strategy PnL.")
    p("Read order: Integrity → distributions (not mean) → Cluster → Toxicity → Decision")

    # ----- Section 1 -----
    p("\n" + "=" * 72)
    p("Section 1 — Data Integrity")
    p("Question: Is the data trustworthy?")
    p("=" * 72)
    if health.empty:
        p("Healthy:       n/a (no health events)")
        p("Sequence gap:  n/a")
        p("Latency:       n/a")
        p("Book freshness:n/a")
    else:
        p(f"Healthy:        {healthy_ratio*100:.2f}%")
        p(f"Sequence gap:   total={gap_total}  window_max={gap_win_max}")
        p("Latency:")
        p(f"  p50: {lat_p50} ms")
        p(f"  p95: {lat_p95} ms")
        p(f"  p99: {lat_p99} ms")
        p(f"Book freshness: median={ba_med:.1f} ms" if ba_med is not None else "Book freshness: n/a")
    p(f"Integrity:      [{'PASS' if integrity_ok else 'FAIL'}]")
    for n in integrity_notes:
        p(f"  · {n}")
    if not integrity_ok:
        p("\n★ STOP — Data Integrity FAIL → Decision=INVALID.")
        p("  Do not interpret Alpha. Bad book/latency/gap fills have no research value.")

    # ----- Section 2 -----
    p("\n" + "=" * 72)
    p("Section 2 — Fill Alpha")
    p("Question: Fill − Matched Market Move  (not PnL)")
    p("Priority: distribution (median/p25/p75) over mean")
    p("=" * 72)
    if not integrity_ok:
        p("(skipped for decision — integrity INVALID; numbers below are not evidence)")
    if alpha_table["Overall"]["fill_w"] is None:
        p("(waiting for fill_path with mid + after_30s)")
    else:
        p(f"{'':12s} {'Fill weighted':>16s} {'Cluster weighted':>18s}")
        for lab in ("Bid", "Ask", "Overall"):
            fw = alpha_table[lab]["fill_w"]
            cw = alpha_table[lab]["cluster_w"]
            p(f"{lab+' Alpha':12s} {_fmt_pct(fw):>16s} {_fmt_pct(cw):>18s}")
        p(f"Direction agree (fill-w vs cluster-w): {'YES' if agree else 'NO ★'}")
        p(f"Benchmark P(+) Δ (fill − matched mid): {_fmt_pp(bench_alpha)}")
        p(f"SPACE class: {space_class or 'PENDING'}")
        if raw_capture is not None and net_edge is not None and total_cost is not None:
            p(f"Raw capture@30s (cluster-w): {_fmt_pct(raw_capture)}")
            p(f"Total cost (fee+slip+lat):   {_fmt_pct(total_cost)}")
            p(f"Net edge:                    {_fmt_pct(net_edge)}")
        p("")
        p("Fill Alpha distribution  (do not trust mean alone):")
        _print_dist(p, "  per-fill MakerAlpha", fill_alpha_dist)
        if pct_fills_positive_alpha is not None:
            p(f"  share of fills with +alpha: {pct_fills_positive_alpha*100:.1f}%")
            if pct_fills_positive_alpha < 0.35 and (fill_alpha_dist.get("mean") or 0) > 0:
                p("  ★ mean>0 but minority of fills — edge likely event-driven / fat tail")
        p("")
        p("Cluster Alpha distribution  (independent liquidity events):")
        _print_dist(p, "  per-cluster mean MakerAlpha", cluster_alpha_dist)
        if (
            alpha_table["Overall"]["fill_w"] is not None
            and alpha_table["Overall"]["cluster_w"] is not None
        ):
            fw, cw = alpha_table["Overall"]["fill_w"], alpha_table["Overall"]["cluster_w"]
            if fw > 0 >= cw:
                p("  ★ Fill+ but Cluster≤0 — edge from few burst fills; unstable")
            elif fw > 0 and cw > 0:
                p("  Fill+ and Cluster+ — credibility higher")

    # ----- Section 3 -----
    p("\n" + "=" * 72)
    p("Section 3 — Toxicity Profile")
    p("Question: Are fills naturally on the wrong side? (record only — no quote changes)")
    p("=" * 72)
    if not toxicity:
        p("(waiting for fill_path)")
    else:
        for label, row in toxicity.items():
            p(f"\n{label}:")
            p("  Immediate toxicity:")
            for hz in ("1s", "5s", "10s"):
                p(f"    {hz}:  {_fmt_pct(row.get(hz))}")
            p("  Recovery:")
            for hz in ("30s", "300s"):
                p(f"    {hz}:  {_fmt_pct(row.get(hz))}")
            # factual pattern note only
            t10, t300 = row.get("10s"), row.get("300s")
            if t10 is not None and t300 is not None:
                if t10 < 0 < t300:
                    p("  Observed pattern: early toxicity + later recovery (fact; not a rule)")
                elif t10 < 0 and t300 <= 0:
                    p("  Observed pattern: sustained adverse (fact; not a rule)")
                elif t10 is not None and t10 > 0:
                    p("  Observed pattern: immediate favorable (fact; not a rule)")
        if c_share is not None:
            p(f"\nPath C (toxic) share: {c_share*100:.1f}%")
        if toxic_bid_ratio is not None:
            p(f"Bid toxic fill ratio: {toxic_bid_ratio*100:.1f}%")
        if adv_mag is not None and sc_mean is not None:
            p(f"mean_adverse vs |spread_capture|: {_fmt_pct(adv_mag)} vs {_fmt_pct(abs(sc_mean))}")
        if tox_dist:
            p("\nToxicity distribution:")
            if tox_dist.get("pct_adverse_10s") is not None:
                p(f"  fills adverse@10s: {tox_dist['pct_adverse_10s']*100:.1f}%")
            if tox_dist.get("fav10"):
                _print_dist(p, "  fav@10s", tox_dist["fav10"])
            w20 = tox_dist.get("worst20_share_of_adverse")
            if w20 is not None:
                p(f"  worst 20% of fills share of adverse loss: {w20*100:.1f}%")
                if w20 >= 0.70:
                    p("  ★ losses concentrated — future value may be 'which quotes NOT to place'")
                    p("    (record only; no cancel/filter rules in freeze)")

    # ----- Section 4 -----
    p("\n" + "=" * 72)
    p("Section 4 — Observed Edge Attribution")
    p("Facts only. Not strategy recommendations. Not filter rules.")
    p("=" * 72)
    if not attr_rows:
        p("(insufficient state slices)")
    else:
        cur_title = None
        for title, idx, n, mean in attr_rows:
            if title != cur_title:
                p(f"\n{title}:")
                cur_title = title
            sign = "positive" if mean > 0 else ("negative" if mean < 0 else "flat")
            p(f"  {idx}: n={n}  E[fav30]={_fmt_pct(mean)}  ({sign})")
        if concentrated:
            p("\nObservation: positive mass concentrated in a single bucket (fact).")

    # ----- Section 5 -----
    p("\n" + "=" * 72)
    p("Section 5 — Decision")
    p("=" * 72)
    p(f"Decision: {verdict}")
    p("")
    if verdict == "INVALID":
        p("Reason:")
        for r in reasons:
            p(f"  - {r}")
        p("\nKeep collecting only after Data Integrity is clean.")
    elif verdict == "COLLECTING":
        p("Reason:")
        for r in reasons:
            p(f"  - {r}")
        p("\nDo not over-interpret before 2000 fills / adequate clusters.")
        p("500 = anomaly check · 2000 = preliminary · 10000 = stability.")
    elif verdict == "PASS":
        p("Maker alpha survives:")
        for r in reasons:
            p(f"  - {r.replace('Maker alpha survives: ', '')}")
        p("\n→ Unlock Stage3 Economic Simulation → Symmetric MM")
    elif verdict == "PARTIAL_PASS":
        p("Partial: market hypothesis holds only in some states/events.")
        for r in reasons:
            p(f"  - {r}")
        p("\n→ Path: Event-driven LP (not all-day Symmetric MM)")
        p("  Still locked: no new filters yet — attribution is observation only.")
    else:
        p("No maker edge under current quote assumption.")
        p("Dominant reasons:")
        for r in reasons:
            p(f"  - {r}")
        p("\nConclusion = hypothesis false (not 'strategy failed'). Avoid futile tuning.")

    p("\nStage3 Unlock Checklist (Economic Simulation):")
    for k, v in stage3_unlock.items():
        p(f"  [{'OK' if v else '·'}] {k}")
    p(f"  Stage3 ready: {'YES' if stage3_ready else 'NO'}")

    p("")
    p("State machine:")
    p("  FAIL          → change hypothesis")
    p("  PARTIAL_PASS  → Event-driven LP")
    p("  PASS          → Economic Simulation → Symmetric MM")
    p("  COLLECTING    → keep collecting")
    p("")
    p("Action: run probe. Look at distributions first, Decision second.")
    p("=" * 72)

    _finish(lines, out_path, decision)
    return decision


def _finish(lines: list[str], out_path: Path | None, decision: dict[str, Any]) -> None:
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        footer = {
            "event": "maker_edge_decision",
            "report": "Maker Edge Report v0.1",
            "phase": "Research Freeze / Data Collection",
            "verdict": decision.get("verdict"),
            "experiment": decision.get("experiment"),
            "space_class": decision.get("space_class"),
            "benchmark_alpha": decision.get("benchmark_alpha"),
            "maker_alpha_mean": decision.get("maker_alpha_mean"),
            "stage3_ready": decision.get("stage3_ready"),
            "stage3_unlock": decision.get("stage3_unlock"),
            "quality": decision.get("quality"),
            "gates": {
                "integrity": decision.get("integrity"),
                "independence": decision.get("independence"),
                "fill_quality": decision.get("fill_quality"),
                "adverse": decision.get("adverse"),
                "stability": decision.get("stability"),
            },
            "reasons": decision.get("reasons"),
        }
        text = "\n".join(lines) + "\n\n---\n" + json.dumps(footer, ensure_ascii=False, indent=2) + "\n"
        out_path.write_text(text, encoding="utf-8")
        print(f"\nReport saved: {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Maker Edge Report v0.1 — Research Freeze")
    ap.add_argument(
        "--dir",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "logs" / "maker_edge"),
    )
    ap.add_argument("--min-fills", type=int, default=PASS_MIN_FILLS_DEFAULT)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    log_dir = Path(args.dir)
    if not log_dir.exists():
        print(f"日志目录不存在: {log_dir}")
        return
    try:
        df = load_events(log_dir)
    except FileNotFoundError as e:
        print(e)
        return
    out = log_dir / "Maker_Edge_Report_v0.1.txt" if args.report else None
    report(df, min_fills=args.min_fills, out_path=out)


if __name__ == "__main__":
    main()
