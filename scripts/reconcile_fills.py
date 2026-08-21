#!/usr/bin/env python3
"""
RECONCILIATION-02 — Local Fill ↔ Venue Trade 1:1 / quantity-level closure

Does NOT resume the probe. Does NOT change quote logic.

Gate: 100% of local fills and venue trades classified into:
  MATCHED | DUPLICATE | ORPHAN_LOCAL | ORPHAN_VENUE | MISMATCH | MALFORMED

Primary link: venue_trade_id when present.
Fallback (historical jsonl has trade_id=None):
  venue_order_id + side + qty + price + timestamp window
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# reuse pagination from recon-01
sys.path.insert(0, str(_ROOT / "scripts"))
from reconcile_account import _env, _fetch_user_trades, _signed_get  # noqa: E402


PX_TICK = 0.1  # BTCUSDT tick
QTY_EPS = 1e-8
TIME_MATCH_SEC = 30.0
TIME_DUP_SEC = 2.0


def _parse_iso(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _ms_ts(ms: int | None) -> float | None:
    if ms is None:
        return None
    return int(ms) / 1000.0


def load_local_fills(log_dir: Path) -> list[dict]:
    fills: list[dict] = []
    for f in sorted(log_dir.glob("*.jsonl")):
        if f.name.startswith("Account_") or f.name.startswith("Maker_") or f.name.startswith("RECON"):
            continue
        for line in f.open():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict) or e.get("event") != "fill":
                continue
            fills.append(e)
    return fills


def normalize_local(e: dict, idx: int) -> dict:
    px = float(e.get("fill_price") or 0)
    qty = float(e.get("amount") or 0)
    side = e.get("side")  # long / short
    venue_oid = e.get("venue_order_id")
    if venue_oid is not None:
        venue_oid = str(venue_oid)
    trade_id = e.get("venue_trade_id") or e.get("trade_id")
    if trade_id in (None, "None", ""):
        trade_id = None
    else:
        trade_id = str(trade_id)
    ts = _parse_iso(e.get("quote_fill_time"))
    malformed = []
    if px <= 0:
        malformed.append("bad_price")
    if qty <= 0:
        malformed.append("bad_qty")
    if side not in ("long", "short"):
        malformed.append("bad_side")
    if not venue_oid:
        malformed.append("missing_venue_order_id")
    return {
        "idx": idx,
        "fill_id": e.get("fill_id"),
        "client_order_id": e.get("client_order_id"),
        "venue_order_id": venue_oid,
        "venue_trade_id": trade_id,
        "side": side,
        "px": px,
        "qty": qty,
        "ts": ts,
        "ts_iso": e.get("quote_fill_time"),
        "commission": e.get("commission"),
        "malformed": malformed,
        "raw_keys": sorted(e.keys()),
    }


def normalize_venue(t: dict, idx: int) -> dict:
    buyer = bool(t.get("buyer"))
    side = "long" if buyer else "short"
    return {
        "idx": idx,
        "venue_trade_id": str(t.get("id")),
        "venue_order_id": str(t.get("orderId")),
        "side": side,
        "px": float(t.get("price") or 0),
        "qty": float(t.get("qty") or 0),
        "ts": _ms_ts(t.get("time")),
        "ts_iso": datetime.fromtimestamp(int(t["time"]) / 1000, tz=timezone.utc).isoformat()
        if t.get("time")
        else None,
        "commission": float(t.get("commission") or 0),
        "commission_asset": t.get("commissionAsset"),
        "maker": t.get("maker"),
        "symbol": t.get("symbol"),
    }


def _compatible(loc: dict, ven: dict) -> tuple[bool, str]:
    if loc["side"] != ven["side"]:
        return False, "side"
    if abs(loc["qty"] - ven["qty"]) > QTY_EPS:
        return False, "qty"
    if abs(loc["px"] - ven["px"]) > PX_TICK + 1e-9:
        return False, "price"
    if loc["ts"] is not None and ven["ts"] is not None:
        if abs(loc["ts"] - ven["ts"]) > TIME_MATCH_SEC:
            return False, "time"
    return True, "ok"


def match(locals_: list[dict], venues: list[dict]) -> dict:
    """Greedy unique matching. Each venue trade consumed at most once."""
    used_v: set[int] = set()
    used_l: set[int] = set()
    matched: list[dict] = []
    mismatch: list[dict] = []
    duplicate: list[dict] = []

    loc_by_tid: dict[str, list[dict]] = defaultdict(list)
    ven_by_tid: dict[str, dict] = {}
    for v in venues:
        ven_by_tid[v["venue_trade_id"]] = v
    for loc in locals_:
        if loc["venue_trade_id"]:
            loc_by_tid[loc["venue_trade_id"]].append(loc)

    # Pass 1: explicit venue_trade_id
    for tid, locs in loc_by_tid.items():
        v = ven_by_tid.get(tid)
        if v is None:
            continue
        primary, *rest = locs
        ok, why = _compatible(primary, v)
        rec = {"local": primary, "venue": v, "link": "venue_trade_id", "compat": why}
        if ok:
            matched.append(rec)
        else:
            rec["mismatch_reason"] = why
            mismatch.append(rec)
        used_v.add(v["idx"])
        used_l.add(primary["idx"])
        for d in rest:
            duplicate.append(
                {"local": d, "venue": v, "link": "venue_trade_id_dup", "reason": "same venue_trade_id"}
            )
            used_l.add(d["idx"])

    # Pass 2: same venue_order_id, greedy best (qty, px, time)
    loc_by_oid: dict[str, list[dict]] = defaultdict(list)
    ven_by_oid: dict[str, list[dict]] = defaultdict(list)
    for loc in locals_:
        if loc["idx"] in used_l or loc["malformed"]:
            continue
        if loc["venue_order_id"]:
            loc_by_oid[loc["venue_order_id"]].append(loc)
    for v in venues:
        if v["idx"] in used_v:
            continue
        ven_by_oid[v["venue_order_id"]].append(v)

    def score(loc: dict, v: dict) -> float:
        ok, _ = _compatible(loc, v)
        if not ok:
            return 1e18
        dt = 0.0
        if loc["ts"] is not None and v["ts"] is not None:
            dt = abs(loc["ts"] - v["ts"])
        return dt + abs(loc["px"] - v["px"]) * 1e-6

    for oid, locs in loc_by_oid.items():
        cands = [v for v in ven_by_oid.get(oid, []) if v["idx"] not in used_v]
        remaining = [x for x in locs if x["idx"] not in used_l]
        for loc in sorted(remaining, key=lambda x: x["ts"] or 0):
            best = None
            best_s = 1e18
            for v in cands:
                if v["idx"] in used_v:
                    continue
                s = score(loc, v)
                if s < best_s:
                    best_s = s
                    best = v
            if best is None or best_s >= 1e17:
                continue
            matched.append({"local": loc, "venue": best, "link": "order_id+px+qty+time", "compat": "ok"})
            used_l.add(loc["idx"])
            used_v.add(best["idx"])

    # Pass 3: remaining locals that share (oid, px, qty) with an already-matched
    # local → DUPLICATE (restart / double-log of same execution)
    matched_sig: dict[tuple, dict] = {}
    for m in matched:
        loc = m["local"]
        v = m["venue"]
        matched_sig[(loc["venue_order_id"], round(loc["px"], 2), round(loc["qty"], 8), loc["side"])] = v

    for loc in locals_:
        if loc["idx"] in used_l or loc["malformed"]:
            continue
        key = (loc["venue_order_id"], round(loc["px"], 2), round(loc["qty"], 8), loc["side"])
        v = matched_sig.get(key)
        if v is None:
            continue
        dt_ok = True
        if loc["ts"] is not None and v["ts"] is not None:
            dt_ok = abs(loc["ts"] - v["ts"]) <= TIME_MATCH_SEC
        if not dt_ok:
            continue
        duplicate.append(
            {
                "local": loc,
                "venue": v,
                "link": "dup_of_matched",
                "reason": "same order/px/qty/side as a matched fill",
            }
        )
        used_l.add(loc["idx"])

    # Pass 4: global leftover by px+qty+side+time (order id mismatch)
    leftover_v = [v for v in venues if v["idx"] not in used_v]
    leftover_l = [x for x in locals_ if x["idx"] not in used_l and not x["malformed"]]
    for loc in leftover_l:
        best = None
        best_s = 1e18
        for v in leftover_v:
            if v["idx"] in used_v:
                continue
            s = score(loc, v)
            if s < best_s:
                best_s = s
                best = v
        if best is None or best_s >= 1e17:
            continue
        matched.append({"local": loc, "venue": best, "link": "global_px_qty_time", "compat": "ok"})
        used_l.add(loc["idx"])
        used_v.add(best["idx"])

    malformed = [x for x in locals_ if x["malformed"]]
    for x in malformed:
        used_l.add(x["idx"])

    orphan_local = [x for x in locals_ if x["idx"] not in used_l]
    orphan_venue = [v for v in venues if v["idx"] not in used_v]

    return {
        "matched": matched,
        "duplicate": duplicate,
        "mismatch": mismatch,
        "malformed": malformed,
        "orphan_local": orphan_local,
        "orphan_venue": orphan_venue,
    }


def _qty(xs, key="qty") -> float:
    return sum(float(x[key]) for x in xs)


def audit_orphan_orders(orphans: list[dict], symbol: str, max_checks: int = 40) -> dict:
    """Cross-check orphan locals against /fapi/v1/order and /userTrades?orderId=."""
    stats = {
        "checked": 0,
        "order_filled_no_trades": 0,
        "order_missing": 0,
        "order_other": 0,
        "trades_found": 0,
    }
    samples: list[dict] = []
    for loc in orphans[:max_checks]:
        oid = loc["venue_order_id"]
        if not oid:
            continue
        stats["checked"] += 1
        try:
            order = _signed_get("/fapi/v1/order", {"symbol": symbol, "orderId": oid})
        except Exception as exc:
            stats["order_missing"] += 1
            samples.append({"oid": oid, "fill_id": loc["fill_id"], "order": "ERR", "detail": str(exc)})
            continue
        st = order.get("status")
        try:
            tr = _signed_get("/fapi/v1/userTrades", {"symbol": symbol, "orderId": oid})
        except Exception:
            tr = []
        ntr = len(tr) if isinstance(tr, list) else 0
        if st == "FILLED" and ntr == 0:
            stats["order_filled_no_trades"] += 1
        elif ntr > 0:
            stats["trades_found"] += 1
        else:
            stats["order_other"] += 1
        if len(samples) < 8:
            samples.append(
                {
                    "oid": oid,
                    "fill_id": loc["fill_id"],
                    "status": st,
                    "execQty": order.get("executedQty"),
                    "avgPrice": order.get("avgPrice"),
                    "userTrades_n": ntr,
                }
            )
    stats["samples"] = samples
    return stats


def write_report(
    out: Path,
    result: dict,
    n_local: int,
    n_venue: int,
    *,
    venue_t_max: str | None = None,
    orphan_audit: dict | None = None,
) -> None:
    m = result["matched"]
    d = result["duplicate"]
    mm = result["mismatch"]
    mal = result["malformed"]
    ol = result["orphan_local"]
    ov = result["orphan_venue"]

    loc_explained = len(m) + len(d) + len(mm) + len(mal) + len(ol)
    ven_explained = len(m) + len(mm) + len(ov)  # dups share venue; orphans leftover
    # every local in exactly one bucket
    # every venue in matched, mismatch, or orphan_venue (dups don't extra-count venue)

    m_qty_l = sum(x["local"]["qty"] for x in m)
    m_qty_v = sum(x["venue"]["qty"] for x in m)
    m_fee_v = sum(x["venue"]["commission"] for x in m)
    dt = [
        abs(x["local"]["ts"] - x["venue"]["ts"])
        for x in m
        if x["local"]["ts"] is not None and x["venue"]["ts"] is not None
    ]
    dt.sort()

    def pctile(a, q):
        if not a:
            return None
        i = min(len(a) - 1, max(0, int(round(q * (len(a) - 1)))))
        return a[i]

    unexplained_local = n_local - (len(m) + len(d) + len(mm) + len(mal))
    # orphan_local IS unexplained in the sense of no venue link, but classified
    classified_local = len(m) + len(d) + len(mm) + len(mal) + len(ol)
    classified_venue = len({x["venue"]["idx"] for x in m + mm} | {x["idx"] for x in ov})

    gate = (
        classified_local == n_local
        and classified_venue == n_venue
        and len(ol) == 0
        and len(ov) == 0
        and len(mm) == 0
        and len(mal) == 0
    )
    # 100% explainable ≠ zero orphans. User asked 100% explainable.
    # We treat orphans as classified. Gate PASS if all rows classified (always if logic sound)
    # Strict gate: no orphans/mismatch/malformed
    explainable = classified_local == n_local and classified_venue == n_venue

    lines = []

    def p(s: str = "") -> None:
        lines.append(s)
    p("=" * 72)
    p("RECONCILIATION-02 — Local Fill ↔ Venue Trade")
    p("MM_EDGE_EXP_001 / probe_v0.1 / TESTNET BTCUSDT")
    p("Probe remains STOPPED")
    p("=" * 72)
    p()
    p("Counts")
    p("-" * 40)
    p(f"Local JSONL fills:     {n_local}")
    p(f"Venue userTrades:      {n_venue}")
    p(f"  MATCHED:             {len(m)}")
    p(f"  DUPLICATE (local):   {len(d)}")
    p(f"  MISMATCH:            {len(mm)}")
    p(f"  MALFORMED (local):   {len(mal)}")
    p(f"  ORPHAN_LOCAL:        {len(ol)}")
    p(f"  ORPHAN_VENUE:        {len(ov)}")
    p(f"Local classified:      {classified_local}/{n_local}")
    p(f"Venue classified:      {classified_venue}/{n_venue}")
    venue_t_max_ts = None
    if venue_t_max:
        p(f"Venue history max (UTC): {venue_t_max}")
        try:
            venue_t_max_ts = datetime.fromisoformat(venue_t_max).timestamp()
        except Exception:
            venue_t_max_ts = None
    if ol and venue_t_max_ts:
        orphan_after = sum(1 for x in ol if x["ts"] is not None and x["ts"] > venue_t_max_ts)
        orphan_before = len(ol) - orphan_after
        p(f"Orphan after venue cutoff: {orphan_after} (userTrades history gap on testnet)")
        p(f"Orphan before cutoff:      {orphan_before}")
    if orphan_audit:
        p()
        p("Orphan order audit (sample)")
        p("-" * 40)
        p(f"  checked:                 {orphan_audit.get('checked')}")
        p(f"  order FILLED, 0 trades:  {orphan_audit.get('order_filled_no_trades')}")
        p(f"  userTrades found:        {orphan_audit.get('trades_found')}")
        for s in orphan_audit.get("samples") or []:
            p(f"  oid={s.get('oid')} status={s.get('status')} exec={s.get('execQty')} trades={s.get('userTrades_n')}")
    p()
    p("Quantity (BTC)")
    p("-" * 40)
    p(f"Matched local qty:     {m_qty_l:.6f}")
    p(f"Matched venue qty:     {m_qty_v:.6f}")
    p(f"Qty residual:          {m_qty_l - m_qty_v:+.8f}")
    p(f"Orphan local qty:      {sum(x['qty'] for x in ol):.6f}")
    p(f"Orphan venue qty:      {sum(x['qty'] for x in ov):.6f}")
    p(f"Duplicate local qty:   {sum(x['local']['qty'] for x in d):.6f}")
    p()
    p("Fee / time (matched only)")
    p("-" * 40)
    p(f"Venue commission sum:  {m_fee_v:.8f} USDT")
    if dt:
        p(f"|Δt| n={len(dt)} p50={pctile(dt,0.5):.3f}s p95={pctile(dt,0.95):.3f}s max={dt[-1]:.3f}s")
    p()
    p("Link methods (matched)")
    p("-" * 40)
    by = defaultdict(int)
    for x in m:
        by[x["link"]] += 1
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        p(f"  {k:28s} {v}")
    p()
    p("Gate")
    p("-" * 40)
    p(f"100% classified:       {'PASS' if explainable else 'FAIL'}")
    p(f"Strict (no orphan/mismatch/malformed): {'PASS' if gate else 'FAIL'}")
    p("Do not resume probe until strict gate PASS or leftovers 100% attributed.")
    p()

    def dump_sample(title: str, rows: list, kind: str, n: int = 8) -> None:
        if not rows:
            return
        p(f"Samples — {title} (showing {min(n, len(rows))}/{len(rows)})")
        p("-" * 40)
        for row in rows[:n]:
            if kind == "match":
                loc, v = row["local"], row["venue"]
                p(
                    f"  fill={loc['fill_id']} oid={loc['venue_order_id']} "
                    f"tid={v['venue_trade_id']} px={loc['px']}/{v['px']} "
                    f"qty={loc['qty']}/{v['qty']} link={row['link']}"
                )
            elif kind == "dup":
                loc, v = row["local"], row["venue"]
                p(
                    f"  fill={loc['fill_id']} oid={loc['venue_order_id']} "
                    f"tid={v['venue_trade_id']} reason={row.get('reason')}"
                )
            elif kind == "local":
                p(
                    f"  fill={row['fill_id']} oid={row['venue_order_id']} "
                    f"px={row['px']} qty={row['qty']} side={row['side']} ts={row['ts_iso']}"
                )
            elif kind == "venue":
                p(
                    f"  tid={row['venue_trade_id']} oid={row['venue_order_id']} "
                    f"px={row['px']} qty={row['qty']} side={row['side']} ts={row['ts_iso']}"
                )
        p()

    dump_sample("ORPHAN_LOCAL", ol, "local")
    dump_sample("ORPHAN_VENUE", ov, "venue")
    dump_sample("DUPLICATE", d, "dup")
    dump_sample("MISMATCH", mm, "match")
    p("=" * 72)

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    sidecar = {
        "experiment_id": "MM_EDGE_EXP_001",
        "recon": "RECONCILIATION-02",
        "n_local": n_local,
        "n_venue": n_venue,
        "matched": len(m),
        "duplicate": len(d),
        "mismatch": len(mm),
        "malformed": len(mal),
        "orphan_local": len(ol),
        "orphan_venue": len(ov),
        "classified_local": classified_local,
        "classified_venue": classified_venue,
        "qty_matched_local": m_qty_l,
        "qty_matched_venue": m_qty_v,
        "qty_orphan_local": sum(x["qty"] for x in ol),
        "qty_orphan_venue": sum(x["qty"] for x in ov),
        "qty_duplicate_local": sum(x["local"]["qty"] for x in d),
        "fee_matched_venue": m_fee_v,
        "strict_gate": gate,
        "classified_gate": explainable,
        "dt_p50_sec": pctile(dt, 0.5),
        "dt_p95_sec": pctile(dt, 0.95),
        "orphan_local_oids": [x["venue_order_id"] for x in ol[:50]],
        "orphan_venue_tids": [x["venue_trade_id"] for x in ov[:50]],
        "venue_history_max": venue_t_max,
        "orphan_audit": orphan_audit,
        "probe": "STOPPED",
    }
    out.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(_ROOT / "logs" / "maker_edge"))
    ap.add_argument("--symbol", default=_env("RECON_SYMBOL", "BTCUSDT"))
    ap.add_argument("--since-days", type=float, default=20.0)
    ap.add_argument("--trades-cache", default="")
    ap.add_argument("--fetch", action="store_true", help="Fetch userTrades from exchange")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    log_dir = Path(args.dir)
    cache = Path(args.trades_cache) if args.trades_cache else log_dir / "venue_trades.json"

    if args.fetch or not cache.exists():
        import time

        end_ms = int(time.time() * 1000)
        start_ms = end_ms - int(args.since_days * 86400 * 1000)
        print(f"[recon-02] fetching userTrades {args.symbol} …")
        trades = _fetch_user_trades(args.symbol, start_ms, end_ms)
        cache.write_text(json.dumps(trades))
        print(f"[recon-02] cached {len(trades)} trades → {cache}")
    else:
        trades = json.loads(cache.read_text())
        print(f"[recon-02] loaded {len(trades)} trades from {cache}")

    raw_fills = load_local_fills(log_dir)
    locals_ = [normalize_local(e, i) for i, e in enumerate(raw_fills)]
    venues = [normalize_venue(t, i) for i, t in enumerate(trades)]
    print(f"[recon-02] local fills={len(locals_)} venue={len(venues)}")

    result = match(locals_, venues)
    venue_t_max = None
    if venues:
        venue_t_max = datetime.fromtimestamp(
            max(int(t["time"]) for t in trades) / 1000, tz=timezone.utc
        ).isoformat()
    orphan_audit = audit_orphan_orders(result["orphan_local"], args.symbol)
    out = Path(args.out) if args.out else log_dir / "RECONCILIATION_02.txt"
    write_report(
        out,
        result,
        len(locals_),
        len(venues),
        venue_t_max=venue_t_max,
        orphan_audit=orphan_audit,
    )
    print(f"[recon-02] saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
