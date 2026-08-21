#!/usr/bin/env python3
"""
Account Ledger Reconciliation — MM_EDGE_EXP_001

Separates:
  MakerAlpha (research markout)  ≠  Account Equity (wallet economics)

Pulls paginated Binance Futures:
  - /fapi/v1/userTrades   (maker flag, commission per fill)
  - /fapi/v1/income       (REALIZED_PNL, COMMISSION, FUNDING_FEE, …)
  - /fapi/v2/account      (wallet + unrealized + position)

Hard gate:
  TAKER_FILLED_COUNT == 0  else  Maker-only = INVALID

Equity identity (target error ≈ 0):
  StartWallet + Σincome_types + (EndUnrealized − StartUnrealized*)
  + Transfers/Adjustments  ≈  EndMarginBalance

* StartUnrealized often unknown → report EndUnrealized separately.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _base_url() -> str:
    env = _env("BINANCE_ENVIRONMENT", "TESTNET").upper()
    if env == "TESTNET":
        return "https://testnet.binancefuture.com"
    if env == "LIVE":
        return "https://fapi.binance.com"
    raise SystemExit(f"BINANCE_ENVIRONMENT must be TESTNET|LIVE, got {env!r}")


def _signed_get(path: str, params: dict | None = None) -> object:
    key = _env("BINANCE_API_KEY")
    sec = _env("BINANCE_API_SECRET")
    if not key or not sec:
        raise SystemExit("BINANCE_API_KEY / BINANCE_API_SECRET required")
    params = dict(params or {})
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60_000
    qs = urllib.parse.urlencode(params)
    sig = hmac.new(sec.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f"{_base_url()}{path}?{qs}&signature={sig}"
    req = urllib.request.Request(url, headers={"X-MBX-APIKEY": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {path} params={params} body={body}") from e


def _fetch_user_trades(symbol: str, start_ms: int, end_ms: int) -> list[dict]:
    """Paginate userTrades by time windows (dedupe by trade id).

    Note: Testnet userTrades can stop returning rows after ~7d of dense history
    even while orders/income continue — RECON-02 must flag that gap separately.
    """
    out: dict[int, dict] = {}
    cursor = start_ms
    safety = 0
    while cursor < end_ms and safety < 2000:
        safety += 1
        chunk_end = min(cursor + 7 * 86400_000 - 1, end_ms)
        batch = _signed_get(
            "/fapi/v1/userTrades",
            {
                "symbol": symbol,
                "startTime": cursor,
                "endTime": chunk_end,
                "limit": 1000,
            },
        )
        assert isinstance(batch, list)
        if not batch:
            cursor = chunk_end + 1
            continue
        for t in batch:
            out[int(t["id"])] = t
        last_t = int(batch[-1]["time"])
        if len(batch) < 1000:
            cursor = max(last_t + 1, chunk_end + 1)
        else:
            nxt = last_t + 1
            if nxt <= cursor:
                nxt = cursor + 1
            cursor = nxt
        time.sleep(0.08)
    return sorted(out.values(), key=lambda x: (int(x["time"]), int(x["id"])))


def _fetch_income(start_ms: int, end_ms: int) -> list[dict]:
    """Paginate income by time only."""
    out: list[dict] = []
    seen: set[tuple] = set()
    cursor = start_ms
    safety = 0
    while cursor < end_ms and safety < 2000:
        safety += 1
        chunk_end = min(cursor + 7 * 86400_000 - 1, end_ms)
        batch = _signed_get(
            "/fapi/v1/income",
            {"startTime": cursor, "endTime": chunk_end, "limit": 1000},
        )
        assert isinstance(batch, list)
        if not batch:
            cursor = chunk_end + 1
            continue
        for row in batch:
            key = (
                row.get("tranId"),
                row.get("time"),
                row.get("incomeType"),
                row.get("income"),
                row.get("asset"),
                row.get("symbol"),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
        last_t = int(batch[-1]["time"])
        if len(batch) < 1000:
            cursor = max(last_t + 1, chunk_end + 1)
        else:
            cursor = last_t + 1
        time.sleep(0.08)
    return out


def _ms_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def load_jsonl_fill_count(log_dir: Path) -> int:
    n = 0
    if not log_dir.exists():
        return 0
    for f in sorted(log_dir.glob("*.jsonl")):
        for line in f.open():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if isinstance(e, dict) and e.get("event") == "fill":
                n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Maker Edge account reconciliation")
    ap.add_argument(
        "--start-wallet",
        type=float,
        default=float(_env("RECON_START_WALLET", "5000")),
        help="Observed starting USDT wallet (default 5000 testnet grant)",
    )
    ap.add_argument(
        "--symbol",
        default=_env("RECON_SYMBOL", "BTCUSDT"),
        help="Futures symbol for userTrades (default BTCUSDT)",
    )
    ap.add_argument(
        "--since-days",
        type=float,
        default=float(_env("RECON_SINCE_DAYS", "14")),
    )
    ap.add_argument(
        "--out",
        default=str(_ROOT / "logs" / "maker_edge" / "Account_Reconciliation.txt"),
    )
    args = ap.parse_args()

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - int(args.since_days * 86400 * 1000)

    print(f"[recon] env={_env('BINANCE_ENVIRONMENT','TESTNET')} base={_base_url()}")
    print(f"[recon] window {_ms_iso(start_ms)} → {_ms_iso(end_ms)}")

    print("[recon] pulling userTrades (paginated)…")
    trades = _fetch_user_trades(args.symbol, start_ms, end_ms)

    print(f"[recon] userTrades={len(trades)}")
    print("[recon] pulling income (paginated)…")
    income = _fetch_income(start_ms, end_ms)
    print(f"[recon] income rows={len(income)}")

    acct = _signed_get("/fapi/v2/account")
    assert isinstance(acct, dict)

    # --- Maker-only hard check ---
    maker_n = sum(1 for t in trades if t.get("maker") is True)
    taker_n = sum(1 for t in trades if t.get("maker") is False)
    unknown_n = len(trades) - maker_n - taker_n
    maker_only_ok = taker_n == 0 and unknown_n == 0 and len(trades) > 0
    maker_only_status = "PASS" if maker_only_ok else ("INVALID" if taker_n > 0 else "NEED VERIFY")

    fee_by_asset: dict[str, float] = defaultdict(float)
    notional = 0.0
    buy_qty = sell_qty = 0.0
    for t in trades:
        fee_by_asset[t.get("commissionAsset") or "?"] += float(t.get("commission") or 0)
        q = float(t.get("qty") or 0)
        px = float(t.get("price") or 0)
        notional += abs(q * px)
        if t.get("buyer"):
            buy_qty += q
        else:
            sell_qty += q
    net_qty = buy_qty - sell_qty

    income_by: dict[str, float] = defaultdict(float)
    for row in income:
        income_by[str(row.get("incomeType"))] += float(row.get("income") or 0)

    wallet = float(acct.get("totalWalletBalance") or 0)
    upnl = float(acct.get("totalUnrealizedProfit") or 0)
    margin = float(acct.get("totalMarginBalance") or 0)
    avail = float(acct.get("availableBalance") or 0)

    positions = []
    for p in acct.get("positions") or []:
        amt = float(p.get("positionAmt") or 0)
        if abs(amt) > 1e-12:
            positions.append(
                {
                    "symbol": p.get("symbol"),
                    "amt": amt,
                    "entry": float(p.get("entryPrice") or 0),
                    "unrealized": float(p.get("unrealizedProfit") or 0),
                }
            )

    start_wallet = float(args.start_wallet)
    income_sum = sum(income_by.values())
    # Identity without known start upnl:
    # EndWallet ≈ StartWallet + Σ income  (transfers included in income types if any)
    implied_end_wallet = start_wallet + income_sum
    wallet_gap = wallet - implied_end_wallet
    equity_now = margin  # wallet + upnl
    equity_vs_start = equity_now - start_wallet

    jsonl_fills = load_jsonl_fill_count(_ROOT / "logs" / "maker_edge")

    lines: list[str] = []
    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    p("=" * 72)
    p("Account Reconciliation — MM_EDGE_EXP_001 / probe_v0.1")
    p("Research markout (MakerAlpha) ≠ Account equity")
    p("=" * 72)
    p()
    p("Status Snapshot")
    p("-" * 40)
    p("Maker Phenomenon       PARTIAL_PASS")
    p("Data Integrity         PASS  (from Maker Edge Report)")
    p(f"Maker-only constraint  {maker_only_status}")
    p("Account Reconciliation NOT COMPLETE" if abs(wallet_gap) > 0.5 else "Account Reconciliation CLOSE")
    p("Economic Edge          UNKNOWN")
    p("Stage 3                LOCKED")
    p("Probe                  STOPPED (no further volume until ledger closes)")
    p()

    p("Section A — Maker-only hard check (exchange userTrades)")
    p("-" * 40)
    p(f"Symbol:              {args.symbol}")
    p(f"Exchange trades:     {len(trades)}")
    p(f"Jsonl fills (local): {jsonl_fills}")
    p(f"MAKER fills:         {maker_n}")
    p(f"TAKER fills:         {taker_n}")
    p(f"Unknown liquidity:   {unknown_n}")
    p(f"TAKER_FILLED_COUNT:  {taker_n}")
    if taker_n > 0:
        p("→ INVALID: sample contaminated by taker fills")
    elif maker_only_ok:
        p("→ PASS: all exchange trades marked maker=true")
    else:
        p("→ NEED VERIFY")
    p(f"Buy qty / Sell qty:  {buy_qty:.6f} / {sell_qty:.6f}")
    p(f"Net inventory (qty): {net_qty:.6f}")
    p(f"Gross notional:      {notional:.4f} USDT")
    for asset, fee in sorted(fee_by_asset.items()):
        p(f"Commission ({asset}): {fee}")
    p()

    p("Section B — Income ledger (paginated, full window)")
    p("-" * 40)
    for k, v in sorted(income_by.items(), key=lambda kv: -abs(kv[1])):
        p(f"  {k:24s} {v:+.8f}")
    p(f"  {'Σ income':24s} {income_sum:+.8f}")
    p()

    p("Section C — Account snapshot (now)")
    p("-" * 40)
    p(f"totalWalletBalance:     {wallet:.8f}")
    p(f"totalUnrealizedProfit:  {upnl:.8f}")
    p(f"totalMarginBalance:     {margin:.8f}   ← equity")
    p(f"availableBalance:       {avail:.8f}")
    if positions:
        p("Open positions:")
        for pos in positions:
            p(
                f"  {pos['symbol']} amt={pos['amt']} entry={pos['entry']} "
                f"upnl={pos['unrealized']}"
            )
    else:
        p("Open positions: (none)")
    p()

    p("Section D — Equity bridge (attempt)")
    p("-" * 40)
    p(f"Start wallet (assumed): {start_wallet:.8f}")
    p(f"+ Σ income:             {income_sum:+.8f}")
    p(f"= Implied end wallet:   {implied_end_wallet:.8f}")
    p(f"Actual end wallet:      {wallet:.8f}")
    p(f"Wallet residual gap:    {wallet_gap:+.8f}")
    p(f"End unrealized:         {upnl:+.8f}")
    p(f"End equity:             {equity_now:.8f}")
    p(f"Equity − start wallet:  {equity_vs_start:+.8f}")
    p()
    p("Interpretation:")
    p("  - Do NOT equate EquityΔ with MakerAlpha failure/success.")
    p("  - Residual gap means incomplete history, wrong start, or missing")
    p("    transfer/adjustment types — Account Reconciliation stays open.")
    p("  - Inventory drift (net qty / open position) can dominate economics")
    p("    even when per-fill markout is slightly positive.")
    p()

    p("Section E — Next required chain")
    p("-" * 40)
    p("QuoteIntent → Submitted → Accepted → Filled")
    p("  → fill_px/qty → liquidity=MAKER → fee")
    p("  → position Δ → realized → funding → equity")
    p("Daily: StartEquity + TradingPnL + Fees + Funding + uPnL + Transfers = EndEquity")
    p("Target residual ≈ 0 before any Stage3 unlock / further volume.")
    p("=" * 72)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # machine-readable sidecar
    sidecar = out.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "experiment_id": "MM_EDGE_EXP_001",
                "maker_only_status": maker_only_status,
                "taker_filled_count": taker_n,
                "maker_filled_count": maker_n,
                "exchange_trades": len(trades),
                "jsonl_fills": jsonl_fills,
                "income_by_type": dict(income_by),
                "income_sum": income_sum,
                "start_wallet_assumed": start_wallet,
                "end_wallet": wallet,
                "end_unrealized": upnl,
                "end_equity": equity_now,
                "wallet_residual_gap": wallet_gap,
                "net_qty": net_qty,
                "fee_by_asset": dict(fee_by_asset),
                "positions": positions,
                "probe": "STOPPED",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[recon] saved {out}")
    print(f"[recon] saved {sidecar}")
    return 0 if maker_only_ok or taker_n == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
