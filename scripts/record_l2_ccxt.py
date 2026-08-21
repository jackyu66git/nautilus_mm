#!/usr/bin/env python3
"""
CCXT 轻量 L2 录音机（不依赖 Nautilus）

用途：在 Nautilus 节点未就绪时，先用代理拉 Binance USDT-M 盘口 + trades，
写入与 Maker Edge 相同的 jsonl schema（book history + 模拟 quote 心跳）。

用法：
  cd nautilus_mm
  source .venv/bin/activate
  export PYTHONPATH=src
  export HTTPS_PROXY=http://127.0.0.1:7897
  python scripts/record_l2_ccxt.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

import ccxt  # type: ignore

from nautilus_mm.recorder import MakerEdgeLogger


def main() -> None:
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or "http://127.0.0.1:7897"
    symbol = os.getenv("CCXT_SYMBOL", "BTC/USDT:USDT")
    poll = float(os.getenv("POLL_SECS", "2"))
    log_dir = os.getenv("MAKER_EDGE_LOG_DIR", str(_ROOT / "logs" / "maker_edge"))

    ex = ccxt.binanceusdm(
        {
            "enableRateLimit": True,
            "proxies": {"http": proxy, "https": proxy},
            "options": {"defaultType": "future"},
        }
    )
    lg = MakerEdgeLogger(log_dir=log_dir, levels=10)
    last_mid = None
    print(f"[ccxt-recorder] {symbol} proxy={proxy} log={log_dir}")
    print("Ctrl+C to stop. This mode records book only (no live orders).")

    while True:
        try:
            ob = ex.fetch_order_book(symbol, limit=10)
            trades = ex.fetch_trades(symbol, limit=100)
            snap = MakerEdgeLogger.snapshot_from_orderbook(
                ob, levels=10, recent_trades=trades, last_mid=last_mid
            )
            if snap.mid:
                last_mid = snap.mid
            now = time.time()
            lg.record_book(snap, now=now)
            # 心跳 quote（不挂单，仅记录可报价位置）
            if snap.best_bid:
                lg.write(
                    {
                        "event": "book_tick",
                        "pair": symbol,
                        "inventory": 0,
                        **snap.to_book_fields(),
                    }
                )
            lg.update_paths(symbol, snap.mid or 0, now=now)
            print(
                f"\r mid={snap.mid:.1f} spread={snap.spread:.2f} obi={snap.obi:+.3f} "
                f"timb={snap.trade_imbalance:+.3f} pending_fills={lg.pending_count}",
                end="",
                flush=True,
            )
        except Exception as e:
            print(f"\nerror: {e}")
        time.sleep(poll)


if __name__ == "__main__":
    main()
