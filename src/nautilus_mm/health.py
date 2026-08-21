"""
Phase 0 — 连接 / 数据健康度

关键指标：
  sequence_gap   — order book 失真信号（>0 需警惕）
  latency_ms     — p50 / p95 / p99 / max（做市看尾部）
  book_age_ms    — quote/fill 使用盘口时的新鲜度
  book/trade update rate
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


def empty_market_state_snapshot() -> dict:
    """预留给 Market Pulse；探针阶段全部为 null，不做预测/下单决策。"""
    return {
        "regime": None,
        "trend_state": None,
        "liquidity_state": None,
        "volatility_state": None,
    }


def _percentile(sorted_vals: list[float], q: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


@dataclass
class ConnectionHealth:
    window_sec: float = 60.0
    report_every_sec: float = 30.0
    _book_ts: deque = field(default_factory=lambda: deque(maxlen=50_000))
    _trade_ts: deque = field(default_factory=lambda: deque(maxlen=50_000))
    _latencies_ms: deque = field(default_factory=lambda: deque(maxlen=5_000))
    _seq_gaps: int = 0
    _seq_gaps_window: deque = field(default_factory=lambda: deque(maxlen=10_000))
    _last_seq: Optional[int] = None
    _last_report: float = 0.0
    _book_count: int = 0
    _trade_count: int = 0
    _last_book_wall: float = 0.0  # 本地收到最新 book 的时间

    def on_book(self, seq: int | None = None, event_ts_ns: int | None = None) -> None:
        now = time.time()
        self._book_ts.append(now)
        self._last_book_wall = now
        self._book_count += 1
        if event_ts_ns is not None and event_ts_ns > 0:
            lat = (now * 1e9 - event_ts_ns) / 1e6
            if -1000 < lat < 60_000:
                self._latencies_ms.append(lat)
        if seq is not None:
            if self._last_seq is not None and seq > self._last_seq + 1:
                gap = seq - self._last_seq - 1
                # Binance L2 update ids often jump across snapshot/reconnect;
                # only count modest gaps as packet loss. Huge jumps → reset.
                if gap <= 1000:
                    self._seq_gaps += gap
                    self._seq_gaps_window.append((now, gap))
            self._last_seq = seq
        self._trim(now)

    def on_trade(self, event_ts_ns: int | None = None) -> None:
        now = time.time()
        self._trade_ts.append(now)
        self._trade_count += 1
        if event_ts_ns is not None and event_ts_ns > 0:
            lat = (now * 1e9 - event_ts_ns) / 1e6
            if -1000 < lat < 60_000:
                self._latencies_ms.append(lat)
        self._trim(now)

    def book_age_ms(self, now: float | None = None) -> Optional[float]:
        """当前时刻距离最近一次 book 更新的年龄（ms）。"""
        if self._last_book_wall <= 0:
            return None
        now = now or time.time()
        return max(0.0, (now - self._last_book_wall) * 1000.0)

    def _trim(self, now: float) -> None:
        cut = now - self.window_sec
        while self._book_ts and self._book_ts[0] < cut:
            self._book_ts.popleft()
        while self._trade_ts and self._trade_ts[0] < cut:
            self._trade_ts.popleft()
        while self._seq_gaps_window and self._seq_gaps_window[0][0] < cut:
            self._seq_gaps_window.popleft()

    def snapshot(self) -> dict:
        now = time.time()
        self._trim(now)
        w = max(self.window_sec, 1e-6)
        lat = sorted(self._latencies_ms)
        gaps_in_window = sum(g for _, g in self._seq_gaps_window)
        book_age = self.book_age_ms(now)
        # Binance depth update ids are not contiguous; gap is observe-only.
        # Healthy = sufficient book rate + fresh book.
        healthy = (
            len(self._book_ts) / w >= 0.5
            and (book_age is None or book_age < 500.0)
        )
        return {
            "event": "health",
            "window_sec": self.window_sec,
            "book_update_rate": len(self._book_ts) / w,
            "trade_update_rate": len(self._trade_ts) / w,
            "latency_ms_mean": (sum(lat) / len(lat)) if lat else None,
            "latency_ms_p50": _percentile(lat, 0.50),
            "latency_ms_p95": _percentile(lat, 0.95),
            "latency_ms_p99": _percentile(lat, 0.99),
            "latency_ms_max": lat[-1] if lat else None,
            "sequence_gap": self._seq_gaps,  # 累计
            "sequence_gap_window": gaps_in_window,  # 近窗
            "book_age_ms": book_age,
            "book_total": self._book_count,
            "trade_total": self._trade_count,
            "healthy": healthy,
        }

    def maybe_report(self) -> Optional[dict]:
        now = time.time()
        if now - self._last_report < self.report_every_sec:
            return None
        self._last_report = now
        return self.snapshot()

    def allow_quoting(self, max_book_age_ms: float = 500.0) -> bool:
        """Gate new quotes on freshness + update rate (not Binance seq jumps)."""
        age = self.book_age_ms()
        if age is None or age >= max_book_age_ms:
            return False
        now = time.time()
        self._trim(now)
        w = max(self.window_sec, 1e-6)
        if len(self._book_ts) / w < 0.5:
            return False
        return True
