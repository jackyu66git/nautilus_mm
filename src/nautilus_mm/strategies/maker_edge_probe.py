"""
MakerEdgeProbe — Nautilus 事件驱动探针（v0）

实验冻结见 nautilus_mm/FREEZE.md — 三不动：
  1. 不动 Quote Logic（无动态 spread / inv skew / AI / Pulse）
  2. 不动成本模型
  3. 不动 PASS/COLLECTING/FAIL 定义

只记录：quote / fill / outcome + Phase0 健康度。
market_state_snapshot 必须保持 null，禁止注入交易决策。
Stage3+ 未解锁前禁止进化为本文件的「聪明报价」。

安全闸（非报价进化）：TTL 撤单、健康度 gate、库存上限、fill 必记。
"""

from __future__ import annotations

import time
from collections import deque
from decimal import Decimal
from typing import Optional

from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import PositiveInt, StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas, TradeTick
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.events import OrderCanceled, OrderDenied, OrderFilled, OrderRejected
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.trading.strategy import Strategy

from nautilus_mm.book_utils import snapshot_from_nautilus_book
from nautilus_mm.health import ConnectionHealth, empty_market_state_snapshot
from nautilus_mm.recorder import MakerEdgeLogger


class MakerEdgeProbeConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    order_qty: Decimal = Decimal("0.001")
    book_depth: PositiveInt = 10
    quote_offset_ticks: PositiveInt = 1
    max_quotes: PositiveInt = 1
    quote_ttl_secs: float = 30.0
    cooldown_secs: float = 60.0
    book_sample_secs: float = 2.0
    log_dir: str = ""
    # 探针：仅在 OBI 极端时挂一侧（吸收叙事），避免噪音
    obi_enter: float = 0.25
    enable_trading: bool = False  # False = 只录盘口不挂单
    # 风险熔断：|inventory| 达上限后只允许减仓方向挂单
    max_abs_inventory: Decimal = Decimal("0.005")


class MakerEdgeProbe(Strategy):
    def __init__(self, config: MakerEdgeProbeConfig) -> None:
        super().__init__(config)
        self.instrument: Instrument | None = None
        self._logger = MakerEdgeLogger(
            log_dir=config.log_dir or None,
            levels=int(config.book_depth),
        )
        self._last_mid: float | None = None
        self._last_book_sample = 0.0
        self._last_quote_ts = 0.0
        self._recent_buys = deque(maxlen=200)
        self._recent_sells = deque(maxlen=200)
        self._quote_id_by_client: dict[str, str] = {}
        self._quote_submit_ts: dict[str, float] = {}
        self._fill_id_by_client: dict[str, str] = {}
        self._liq_high = 0.0
        self._liq_low = 0.0
        self._health = ConnectionHealth(window_sec=60.0, report_every_sec=30.0)
        self._quoting_halted = False

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return

        # 启动清场：避免上次硬杀残留挂单污染实验
        try:
            self.cancel_all_orders(self.config.instrument_id)
            self.log.info("Startup cancel_all_orders issued", LogColor.BLUE)
        except Exception as exc:
            self.log.warning(f"Startup cancel_all failed: {exc}")

        self.subscribe_order_book_deltas(
            instrument_id=self.config.instrument_id,
            book_type=BookType.L2_MBP,
            depth=int(self.config.book_depth),
        )
        self.subscribe_trade_ticks(self.config.instrument_id)
        exp = self._logger.experiment
        self._logger.write_experiment_start(
            extra={
                "instrument_id": str(self.config.instrument_id),
                "enable_trading": bool(self.config.enable_trading),
                "quote_ttl_secs": float(self.config.quote_ttl_secs),
                "max_abs_inventory": str(self.config.max_abs_inventory),
                "log_dir": str(self._logger.log_dir),
            }
        )
        self.log.info(
            f"Experiment {exp['experiment_id']} | {exp['probe_version']} | "
            f"quote/fee/exchange=frozen | log={self._logger.log_dir} | "
            f"trading={self.config.enable_trading} ttl={self.config.quote_ttl_secs}s "
            f"max_inv={self.config.max_abs_inventory}",
            LogColor.GREEN,
        )
        self.log.info(
            "Research Freeze: Data Collection only — no Pulse / no quote evolution",
            LogColor.BLUE,
        )

    def on_stop(self) -> None:
        try:
            self.cancel_all_orders(self.config.instrument_id)
        except Exception as exc:
            self.log.warning(f"Stop cancel_all failed: {exc}")
        self.log.info("MakerEdgeProbe stopped")

    # ------------------------------------------------------------------ #
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
            liq_low=self._liq_low or None,
            liq_high=self._liq_high or None,
        )
        if snap.mid:
            self._last_mid = snap.mid
            self._liq_high = max(self._liq_high or snap.mid, snap.mid)
            self._liq_low = min(self._liq_low or snap.mid, snap.mid) if self._liq_low else snap.mid
        return snap

    def _inventory(self) -> float:
        try:
            positions = self.cache.positions_open(instrument_id=self.config.instrument_id)
        except TypeError:
            positions = [
                p
                for p in self.cache.positions_open()
                if p.instrument_id == self.config.instrument_id
            ]
        if not positions:
            return 0.0
        inv = 0.0
        for pos in positions:
            qty = float(pos.quantity)
            inv += -qty if pos.is_short else qty
        return inv

    def _open_orders(self):
        try:
            return list(self.cache.orders_open(instrument_id=self.config.instrument_id))
        except TypeError:
            return [
                o
                for o in self.cache.orders_open()
                if o.instrument_id == self.config.instrument_id
            ]

    def _expire_stale_quotes(self, now: float) -> None:
        """Cancel GTC quotes older than quote_ttl_secs."""
        ttl = float(self.config.quote_ttl_secs)
        if ttl <= 0:
            return
        for order in self._open_orders():
            cid = order.client_order_id.value
            submitted = self._quote_submit_ts.get(cid)
            if submitted is None:
                # 非本进程跟踪的单（启动残留等）— 一并撤掉
                self.log.warning(f"TTL cancel untracked open order {cid}")
                self.cancel_order(order)
                continue
            if now - submitted >= ttl:
                self.log.info(f"TTL cancel {cid} age={now - submitted:.1f}s", LogColor.YELLOW)
                self.cancel_order(order)

    def _inventory_allows(self, side: OrderSide, inv: float) -> bool:
        max_abs = float(self.config.max_abs_inventory)
        if max_abs <= 0:
            return True
        if abs(inv) < max_abs:
            return True
        # 超限：只允许减仓方向
        if inv >= max_abs and side == OrderSide.SELL:
            return True
        if inv <= -max_abs and side == OrderSide.BUY:
            return True
        return False

    def _release_quote_client(self, cid: str, reason: str, snap=None) -> None:
        qid = self._quote_id_by_client.pop(cid, None)
        self._quote_submit_ts.pop(cid, None)
        if qid is not None:
            self._logger.cancel_quote(quote_id=qid, reason=reason, snap=snap)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        now = time.time()
        # Phase 0 health
        seq = getattr(deltas, "sequence", None)
        ts_event = getattr(deltas, "ts_event", None)
        self._health.on_book(seq=int(seq) if seq is not None else None, event_ts_ns=ts_event)
        report = self._health.maybe_report()
        if report:
            self._logger.write(report)
            gap_w = report.get("sequence_gap_window", 0)
            color = LogColor.RED if gap_w or not report.get("healthy") else LogColor.CYAN
            self.log.info(
                f"Phase0 book/s={report['book_update_rate']:.1f} "
                f"trade/s={report['trade_update_rate']:.1f} "
                f"lat_p50/p99/max={report['latency_ms_p50']}/"
                f"{report['latency_ms_p99']}/{report['latency_ms_max']} "
                f"gap_win={gap_w} book_age_ms={report.get('book_age_ms')}",
                color,
            )

        # TTL 撤单：与报价逻辑无关的生命周期闭环
        self._expire_stale_quotes(now)

        snap = self._current_snap()
        if snap is None or snap.mid <= 0:
            return

        if now - self._last_book_sample >= float(self.config.book_sample_secs):
            self._last_book_sample = now
            self._logger.record_book(
                snap,
                now=now,
                emit_mid_tick=True,
                pair=str(self.config.instrument_id),
            )
            inv_fields = self._logger.update_inventory(self._inventory(), now=now)
            self._logger.write(
                {
                    "event": "inventory_tick",
                    "pair": str(self.config.instrument_id),
                    **inv_fields,
                    "market_state_snapshot": empty_market_state_snapshot(),
                    **snap.to_book_fields(),
                }
            )

        # 推进 fill path
        self._logger.update_paths(str(self.config.instrument_id), snap.mid, now=now)

        if not self.config.enable_trading:
            return
        if not self._health.allow_quoting():
            if not self._quoting_halted:
                self._quoting_halted = True
                self.log.warning("Quoting halted: health gate (stale book / low update rate)")
            return
        if self._quoting_halted:
            self._quoting_halted = False
            self.log.info("Quoting resumed: health OK", LogColor.GREEN)

        if now - self._last_quote_ts < float(self.config.cooldown_secs):
            return
        if len(self._open_orders()) >= int(self.config.max_quotes):
            return

        if self.instrument is None:
            return

        # 简单吸收探针：OBI 极端 → 挂被动单
        tick = float(self.instrument.price_increment)
        offset = int(self.config.quote_offset_ticks) * tick
        qty = self.instrument.make_qty(self.config.order_qty)
        inv = self._inventory()

        if snap.obi >= float(self.config.obi_enter):
            side = OrderSide.SELL
            if not self._inventory_allows(side, inv):
                return
            price = self.instrument.make_price(snap.best_ask + offset)
            self._submit_quote(side, price, qty, snap, reason="obi_bid_thick")
        elif snap.obi <= -float(self.config.obi_enter):
            side = OrderSide.BUY
            if not self._inventory_allows(side, inv):
                return
            price = self.instrument.make_price(snap.best_bid - offset)
            self._submit_quote(side, price, qty, snap, reason="obi_ask_thick")

    def on_trade_tick(self, tick: TradeTick) -> None:
        now = time.time()
        self._health.on_trade(event_ts_ns=getattr(tick, "ts_event", None))
        qty = float(tick.size)
        # Aggressor side
        try:
            from nautilus_trader.model.enums import AggressorSide

            if tick.aggressor_side == AggressorSide.BUYER:
                self._recent_buys.append((now, qty))
            elif tick.aggressor_side == AggressorSide.SELLER:
                self._recent_sells.append((now, qty))
        except Exception:
            self._recent_buys.append((now, qty * 0.5))
            self._recent_sells.append((now, qty * 0.5))

        snap_mid = self._last_mid or float(tick.price)
        self._logger.update_paths(str(self.config.instrument_id), snap_mid, now=now)

    def _submit_quote(self, side: OrderSide, price: Price, qty: Quantity, snap, reason: str) -> None:
        assert self.instrument is not None
        order = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=side,
            quantity=qty,
            price=price,
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        qside = "bid" if side == OrderSide.BUY else "ask"
        cid = order.client_order_id.value
        # 先 submit，成功后再记 quote（避免幽灵 quote_created）
        try:
            self.submit_order(order)
        except Exception as exc:
            self.log.error(f"submit_order failed: {exc}")
            return

        qid = self._logger.create_quote(
            pair=str(self.config.instrument_id),
            side=qside,
            quote_price=float(price),
            inventory=self._inventory(),
            snap=snap,
            reason=reason,
            state=empty_market_state_snapshot(),  # 故意不接 Market Pulse
            extra={"book_age_ms": self._health.book_age_ms()},
        )
        self._quote_id_by_client[cid] = qid
        self._quote_submit_ts[cid] = time.time()
        self._last_quote_ts = time.time()
        self.log.info(f"QUOTE {qside} {price} qty={qty} reason={reason}", LogColor.BLUE)

    def on_order_canceled(self, event: OrderCanceled) -> None:
        cid = event.client_order_id.value
        snap = self._current_snap()
        self._release_quote_client(cid, reason="canceled", snap=snap)

    def on_order_rejected(self, event: OrderRejected) -> None:
        cid = event.client_order_id.value
        reason = getattr(event, "reason", None) or "rejected"
        self.log.warning(f"OrderRejected {cid}: {reason}")
        snap = self._current_snap()
        self._release_quote_client(cid, reason=f"rejected:{reason}", snap=snap)

    def on_order_denied(self, event: OrderDenied) -> None:
        cid = event.client_order_id.value
        reason = getattr(event, "reason", None) or "denied"
        self.log.warning(f"OrderDenied {cid}: {reason}")
        snap = self._current_snap()
        self._release_quote_client(cid, reason=f"denied:{reason}", snap=snap)

    def on_order_filled(self, event: OrderFilled) -> None:
        cid = event.client_order_id.value
        qid = self._quote_id_by_client.get(cid)
        snap = self._current_snap()
        # snap 缺失仍必须记 fill（book 字段可空）
        side = "long" if event.order_side == OrderSide.BUY else "short"
        det = self._logger.book_deterioration(side)
        fill_reason = "toxic_passive" if det.get("pre_5s_deteriorated") else "maker_hit"

        order = self.cache.order(event.client_order_id)
        terminal = True
        if order is not None:
            terminal = bool(order.is_closed) or float(order.leaves_qty) <= 0

        fill_id = self._logger.log_fill(
            pair=str(self.config.instrument_id),
            side=side,
            fill_price=float(event.last_px),
            amount=float(event.last_qty),
            inventory=self._inventory(),
            snap=snap,
            order_type="limit",
            quote_id=qid,
            fill_reason=fill_reason,
            state=empty_market_state_snapshot(),
            quote_terminal=terminal,
            extra={
                "client_order_id": cid,
                "venue_order_id": str(event.venue_order_id),
                "trade_id": str(event.trade_id),
                "venue_trade_id": str(event.trade_id),
                "exchange_ts_ns": int(event.ts_event) if getattr(event, "ts_event", None) else None,
                "local_ts": time.time(),
                "book_age_ms": self._health.book_age_ms(),
                "leaves_qty": float(order.leaves_qty) if order is not None else None,
                # Maker-only hard evidence (do not trust post_only param alone)
                "liquidity_side": str(event.liquidity_side),
                "is_maker": event.liquidity_side.name == "MAKER"
                if hasattr(event.liquidity_side, "name")
                else str(event.liquidity_side) == "MAKER",
                "commission": float(event.commission) if event.commission is not None else None,
                "commission_currency": (
                    str(event.commission.currency) if event.commission is not None else None
                ),
                "post_only": True,
                "execution_type": "TRADE",
            },
        )
        self._fill_id_by_client[cid] = fill_id
        if terminal:
            self._quote_id_by_client.pop(cid, None)
            self._quote_submit_ts.pop(cid, None)
        self.log.info(
            f"FILL {side} px={event.last_px} qty={event.last_qty} "
            f"reason={fill_reason} terminal={terminal} book={'ok' if snap else 'none'}",
            LogColor.YELLOW,
        )
