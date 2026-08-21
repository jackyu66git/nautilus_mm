"""
Event-State Observability Probe — MM_EDGE_EXP_002

Type:    Data Collection / Observability Experiment
Strategy: NONE (no quotes, no orders, no trading)
Purpose: Capture immutable pre-fill Event State

EXP_001 remains FROZEN. This probe never submits orders.
"""

from __future__ import annotations

import time
from collections import deque

from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import PositiveInt, StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas, TradeTick
from nautilus_trader.model.enums import AggressorSide, BookType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.trading.strategy import Strategy

from nautilus_mm.book_utils import snapshot_from_nautilus_book
from nautilus_mm.event_ledger import ImmutableEventLedger
from nautilus_mm.health import ConnectionHealth


class EventStateProbeConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    book_depth: PositiveInt = 10
    log_dir: str = ""
    prefill_window_sec: float = 5.0
    prefill_margin_sec: float = 0.25
    large_trade_qty: float = 0.1
    # Log every book delta batch (raw). Do not downsample.
    log_every_book_delta: bool = True


class EventStateProbe(Strategy):
    """Read-only market observability — immutable event ledger only."""

    def __init__(self, config: EventStateProbeConfig) -> None:
        super().__init__(config)
        self.instrument: Instrument | None = None
        self._ledger = ImmutableEventLedger(
            log_dir=config.log_dir or None,
            prefill_window_sec=float(config.prefill_window_sec),
            prefill_margin_sec=float(config.prefill_margin_sec),
            large_trade_qty=float(config.large_trade_qty),
            book_levels=int(config.book_depth),
        )
        self._health = ConnectionHealth(window_sec=60.0, report_every_sec=30.0)
        self._last_mid: float | None = None
        self._recent_buys: deque[tuple[float, float]] = deque(maxlen=500)
        self._recent_sells: deque[tuple[float, float]] = deque(maxlen=500)

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return

        self.subscribe_order_book_deltas(
            instrument_id=self.config.instrument_id,
            book_type=BookType.L2_MBP,
            depth=int(self.config.book_depth),
        )
        self.subscribe_trade_ticks(self.config.instrument_id)

        exp = self._ledger.experiment
        ident = self._ledger.run_identity
        self._ledger.write_experiment_start(
            extra={
                "instrument_id": str(self.config.instrument_id),
                "log_dir": str(self._ledger.log_dir),
                "log_every_book_delta": bool(self.config.log_every_book_delta),
                "depends_on": "MM_EDGE_EXP_001 / v0.1 FROZEN",
            }
        )
        self.log.info(
            f"EXP_002 Event-State Observability | {exp['experiment_id']} | "
            f"{exp['probe_version']} | run={ident['run_id']} session={ident['session_id']} | "
            f"trading=NO | log={self._ledger.log_dir}",
            LogColor.GREEN,
        )

    def submit_order(self, *args, **kwargs):  # noqa: ANN002
        raise RuntimeError(
            "MM_EDGE_EXP_002 forbids submit_order — observability probe, trading=NO"
        )

    def submit_order_list(self, *args, **kwargs):  # noqa: ANN002
        raise RuntimeError(
            "MM_EDGE_EXP_002 forbids submit_order_list — observability probe, trading=NO"
        )

    def on_stop(self) -> None:
        try:
            self._ledger.write_experiment_stop()
        except Exception as exc:
            self.log.warning(f"experiment_stop write failed: {exc}")
        self.log.info("EventStateProbe stopped (no orders were submitted)")

    def _trade_qty_window(self, window_sec: float = 20.0) -> tuple[float, float]:
        now = time.time()
        buy = sum(q for t, q in self._recent_buys if now - t <= window_sec)
        sell = sum(q for t, q in self._recent_sells if now - t <= window_sec)
        return buy, sell

    def _current_snap(self):
        book = self.cache.order_book(self.config.instrument_id)
        if book is None:
            return None
        buy, sell = self._trade_qty_window()
        snap = snapshot_from_nautilus_book(
            book,
            levels=int(self.config.book_depth),
            recent_buy_qty=buy,
            recent_sell_qty=sell,
            last_mid=self._last_mid,
        )
        if snap.mid:
            self._last_mid = snap.mid
        return snap

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        seq = getattr(deltas, "sequence", None)
        ts_event = getattr(deltas, "ts_event", None)
        self._health.on_book(seq=int(seq) if seq is not None else None, event_ts_ns=ts_event)

        report = self._health.maybe_report()
        if report:
            self._ledger.write({**report, "event": "phase0_health"})

        if not self.config.log_every_book_delta:
            return

        snap = self._current_snap()
        if snap is None or snap.mid <= 0:
            return

        delta_count = len(getattr(deltas, "deltas", []) or [])
        exchange_ts = int(ts_event) if ts_event is not None else None
        self._ledger.log_book_state(
            pair=str(self.config.instrument_id),
            snap=snap,
            exchange_ts_ns=exchange_ts,
            local_ts_epoch=time.time(),
            sequence=int(seq) if seq is not None else None,
            delta_count=delta_count,
            event_type="book_update",
        )

    def on_trade_tick(self, tick: TradeTick) -> None:
        ts_event = getattr(tick, "ts_event", None)
        self._health.on_trade(event_ts_ns=ts_event)

        qty = float(tick.size)
        price = float(tick.price)
        now = time.time()
        trade_side = "unknown"
        aggressor = str(getattr(tick, "aggressor_side", ""))
        try:
            if tick.aggressor_side == AggressorSide.BUYER:
                trade_side = "buy"
                self._recent_buys.append((now, qty))
            elif tick.aggressor_side == AggressorSide.SELLER:
                trade_side = "sell"
                self._recent_sells.append((now, qty))
        except Exception:
            trade_side = "unknown"

        exchange_ts = int(ts_event) if ts_event is not None else None
        trade_id = str(getattr(tick, "trade_id", "") or getattr(tick, "id", "") or "")
        self._ledger.log_aggressive_trade(
            pair=str(self.config.instrument_id),
            price=price,
            qty=qty,
            trade_side=trade_side,
            exchange_ts_ns=exchange_ts,
            local_ts_epoch=now,
            aggressor_side=aggressor,
            trade_id=trade_id or None,
            snap=self._current_snap(),
        )
