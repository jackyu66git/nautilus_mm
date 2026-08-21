#!/usr/bin/env python3
"""
RECONCILIATION-03 — Order-level evidence for ORPHAN_LOCAL (post userTrades cutoff)

Does NOT resume probe. Does NOT reclassify as MATCHED.

For each ORPHAN_LOCAL from RECON-02, query /fapi/v1/order and validate:
  status == FILLED
  executedQty ~= sum(local qty per order)
  avgPrice ~= local weighted avg
  side consistent

Reclassify passing rows as:
  VENUE_CONFIRMED_NO_TRADE_HISTORY
  (Order evidence only — no userTrades row on Testnet after cutoff)

See TESTNET_LIMITATIONS.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "src"))

from reconcile_fills import (  # noqa: E402
    load_local_fills,
    match,
    normalize_local,
    normalize_venue,
)
from reconcile_account import _env, _fetch_user_trades, _signed_get  # noqa: E402

PX_TICK = 0.1
QTY_EPS = 1e-8


def _order_side_to_local(side: str) -> str:
    return "long" if side.upper() == "BUY" else "short"


def fetch_order(symbol: str, order_id: str, cache: dict) -> dict | None:
    if order_id in cache:
        return cache[order_id]
    try:
        o = _signed_get("/fapi/v1/order", {"symbol": symbol, "orderId": order_id})
    except Exception as exc:
        cache[order_id] = {"_error": str(exc)}
        return cache[order_id]
    cache[order_id] = o if isinstance(o, dict) else {"_error": "bad_response"}
    time.sleep(0.05)
    return cache[order_id]


def validate_order_group(fills: list[dict], order: dict) -> tuple[str, list[str]]:
    """Return (classification, reasons)."""
    reasons: list[str] = []
    if order.get("_error"):
        return "ORPHAN_LOCAL_UNCONFIRMED", [f"order_api_error:{order['_error']}"]
    st = order.get("status")
    exec_qty = float(order.get("executedQty") or 0)
    avg_px = float(order.get("avgPrice") or 0)
    local_qty = sum(f["qty"] for f in fills)
    if exec_qty <= 0:
        return "ORPHAN_LOCAL_UNCONFIRMED", [f"status={st} executedQty=0"]
    # Partial fill then TTL cancel: status=CANCELED but executedQty>0
    if st not in ("FILLED", "CANCELED"):
        return "ORPHAN_LOCAL_UNCONFIRMED", [f"status={st}"]
    if abs(local_qty - exec_qty) > QTY_EPS:
        reasons.append(f"qty local={local_qty} order={exec_qty}")
    wavg = sum(f["px"] * f["qty"] for f in fills) / local_qty if local_qty else 0
    if avg_px > 0 and abs(wavg - avg_px) > PX_TICK + 1e-6:
        reasons.append(f"px local_wavg={wavg:.2f} order_avg={avg_px:.2f}")
    order_side = _order_side_to_local(str(order.get("side", "")))
    for f in fills:
        if f["side"] != order_side:
            reasons.append(f"side local={f['side']} order={order_side}")
            break
    if reasons:
        return "ORDER_MISMATCH", reasons
    if st == "CANCELED":
        return "VENUE_PARTIAL_ORDER_CANCELED", []
    return "VENUE_CONFIRMED_NO_TRADE_HISTORY", []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(_ROOT / "logs" / "maker_edge"))
    ap.add_argument("--symbol", default=_env("RECON_SYMBOL", "BTCUSDT"))
    ap.add_argument("--trades-cache", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    log_dir = Path(args.dir)
    cache_path = Path(args.trades_cache) if args.trades_cache else log_dir / "venue_trades.json"
    trades = json.loads(cache_path.read_text()) if cache_path.exists() else []

    raw = load_local_fills(log_dir)
    locals_ = [normalize_local(e, i) for i, e in enumerate(raw)]
    venues = [normalize_venue(t, i) for i, t in enumerate(trades)]
    r02 = match(locals_, venues)
    orphans = r02["orphan_local"]

    by_oid: dict[str, list[dict]] = defaultdict(list)
    for f in orphans:
        if f.get("venue_order_id"):
            by_oid[f["venue_order_id"]].append(f)

    order_cache: dict[str, dict] = {}
    fill_class: dict[str, tuple[str, list[str], dict | None]] = {}
    counts = defaultdict(int)
    order_rows: list[dict] = []

    for oid, fills in sorted(by_oid.items()):
        order = fetch_order(args.symbol, oid, order_cache)
        cls, reasons = validate_order_group(fills, order or {})
        counts[cls] += len(fills)
        order_rows.append(
            {
                "venue_order_id": oid,
                "classification": cls,
                "n_local_fills": len(fills),
                "local_qty": sum(f["qty"] for f in fills),
                "order_executedQty": order.get("executedQty") if order else None,
                "order_avgPrice": order.get("avgPrice") if order else None,
                "order_status": order.get("status") if order else None,
                "order_updateTime": order.get("updateTime") if order else None,
                "reasons": reasons,
            }
        )
        for f in fills:
            fill_class[f["fill_id"]] = (cls, reasons, order)

    # Summary from RECON-02 matched
    n_matched = len(r02["matched"])
    n_dup = len(r02["duplicate"])
    n_mismatch = len(r02["mismatch"])
    n_mal = len(r02["malformed"])
    n_confirmed = counts["VENUE_CONFIRMED_NO_TRADE_HISTORY"]
    n_partial_canceled = counts["VENUE_PARTIAL_ORDER_CANCELED"]
    n_order_mismatch = counts["ORDER_MISMATCH"]
    n_unconfirmed = counts["ORPHAN_LOCAL_UNCONFIRMED"]
    n_local = len(locals_)

    venue_t_max = None
    if trades:
        venue_t_max = datetime.fromtimestamp(
            max(int(t["time"]) for t in trades) / 1000, tz=timezone.utc
        ).isoformat()

    order_evidence_ok = (
        n_unconfirmed == 0
        and n_order_mismatch == 0
        and (n_confirmed + n_partial_canceled) == len(orphans)
    )
    classified = (
        n_matched + n_dup + n_mismatch + n_mal
        + n_confirmed + n_partial_canceled + n_order_mismatch + n_unconfirmed
    )

    lines: list[str] = []

    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    p("=" * 72)
    p("RECONCILIATION-03 — Order-level evidence (ORPHAN_LOCAL backfill)")
    p("MM_EDGE_EXP_001 / probe_v0.1 / TESTNET BTCUSDT")
    p("Probe remains STOPPED")
    p("=" * 72)
    p()
    p("Prior RECON-02 (trade-level)")
    p("-" * 40)
    p(f"MATCHED (Order+Trade):              {n_matched}")
    p(f"DUPLICATE:                          {n_dup}")
    p(f"MISMATCH:                           {n_mismatch}")
    p(f"MALFORMED:                          {n_mal}")
    p(f"ORPHAN_LOCAL (pre-03):              {len(orphans)}")
    if venue_t_max:
        p(f"userTrades history max (UTC):       {venue_t_max}")
    p()
    p("RECON-03 order-level reclassification")
    p("-" * 40)
    p(f"VENUE_CONFIRMED_NO_TRADE_HISTORY:   {n_confirmed}")
    p(f"VENUE_PARTIAL_ORDER_CANCELED:       {n_partial_canceled}")
    p(f"ORDER_MISMATCH:                     {n_order_mismatch}")
    p(f"ORPHAN_LOCAL_UNCONFIRMED:           {n_unconfirmed}")
    p(f"Unique orders checked:              {len(by_oid)}")
    p()
    p("Evidence grades (permanent taxonomy)")
    p("-" * 40)
    p("MATCHED                          = Order + Trade row (dual evidence)")
    p("VENUE_CONFIRMED_NO_TRADE_HISTORY = Order FILLED, no userTrades row")
    p("VENUE_PARTIAL_ORDER_CANCELED     = Partial fill, order later CANCELED (TTL)")
    p("ORDER_MISMATCH                   = Order exists but qty/px/side disagree")
    p("ORPHAN_LOCAL_UNCONFIRMED         = No reliable order evidence")
    p()
    p("Gates")
    p("-" * 40)
    p(f"RECON-02 classification (all buckets): {'PASS' if classified == n_local else 'FAIL'}")
    p(f"Order-level closure (887 backfill):    {'PASS' if order_evidence_ok else 'FAIL'}")
    p(f"Strict trade-level closure:            FAIL (by design until live trade_id ledger)")
    p()
    p("Testnet limitation")
    p("-" * 40)
    p("userTrades history is NOT guaranteed complete after observed cutoff.")
    p("Order-level FILLED status remains queryable via /fapi/v1/order.")
    p("Do NOT treat VENUE_CONFIRMED fills as fake or duplicate.")
    p()

    fails = [r for r in order_rows if r["classification"] in ("ORDER_MISMATCH", "ORPHAN_LOCAL_UNCONFIRMED")]
    if fails:
        p(f"Non-confirmed orders (showing {min(8, len(fails))}/{len(fails)})")
        p("-" * 40)
        for r in fails[:8]:
            p(
                f"  oid={r['venue_order_id']} cls={r['classification']} "
                f"local_qty={r['local_qty']} exec={r['order_executedQty']} reasons={r['reasons']}"
            )
        p()

    p("=" * 72)

    out = Path(args.out) if args.out else log_dir / "RECONCILIATION_03.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    sidecar = {
        "experiment_id": "MM_EDGE_EXP_001",
        "recon": "RECONCILIATION-03",
        "n_local": n_local,
        "matched_trade_level": n_matched,
        "orphan_local_pre03": len(orphans),
        "venue_confirmed_no_trade_history": n_confirmed,
        "venue_partial_order_canceled": n_partial_canceled,
        "order_mismatch": n_order_mismatch,
        "orphan_local_unconfirmed": n_unconfirmed,
        "unique_orders_checked": len(by_oid),
        "userTrades_cutoff_utc": venue_t_max,
        "recon02_classification_pass": classified == n_local,
        "order_level_closure_pass": order_evidence_ok,
        "strict_trade_level_pass": False,
        "probe": "STOPPED",
        "order_rows": order_rows,
    }
    out.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"[recon-03] saved {out}")
    return 0 if order_evidence_ok else 1


if __name__ == "__main__":
    sys.exit(main())
