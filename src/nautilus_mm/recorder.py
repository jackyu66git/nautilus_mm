"""
Maker Edge 事件记录器 — Execution Reality Layer（Nautilus / CCXT 共用）

事件：
- quote_created / quote_canceled / quote_filled
- fill / fill_path / fill_exit

默认输出：nautilus_mm/logs/maker_edge/YYYYMMDD.jsonl
（与 Freqtrade MakerEdgeProbe schema 对齐，可用同一 analyze 脚本）
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from nautilus_mm.experiment import load_experiment_meta, stamp_event

logger = logging.getLogger(__name__)


def empty_market_state_snapshot() -> dict:
    """Market Pulse 预留位；探针阶段保持 null，不做交易决策。"""
    return {
        "regime": None,
        "trend_state": None,
        "liquidity_state": None,
        "volatility_state": None,
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime | float | None = None) -> str:
    if ts is None:
        t = _utc_now()
    elif isinstance(ts, (int, float)):
        t = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        t = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return t.isoformat()


@dataclass
class MicroSnapshot:
    best_bid: float = 0.0
    best_ask: float = 0.0
    mid: float = 0.0
    spread: float = 0.0
    bid_depth_1: float = 0.0
    ask_depth_1: float = 0.0
    bid_depth_5: float = 0.0
    ask_depth_5: float = 0.0
    bid_depth: float = 0.0  # top-N
    ask_depth: float = 0.0
    obi: float = 0.0
    delta: float = 0.0
    trade_imbalance: float = 0.0  # (buy-sell)/(buy+sell) on recent trades
    delta_efficiency: float = 0.0
    liquidation_distance: float = 0.0

    def to_book_fields(self) -> dict[str, float]:
        return {
            "bid_price": self.best_bid,
            "ask_price": self.best_ask,
            "mid": self.mid,
            "spread": self.spread,
            "bid_depth_1": self.bid_depth_1,
            "ask_depth_1": self.ask_depth_1,
            "bid_depth_5": self.bid_depth_5,
            "ask_depth_5": self.ask_depth_5,
            "bid_depth": self.bid_depth,
            "ask_depth": self.ask_depth,
            "obi": self.obi,
            "delta": self.delta,
            "trade_imbalance": self.trade_imbalance,
            "delta_efficiency": self.delta_efficiency,
            "liquidation_distance": self.liquidation_distance,
            # 兼容旧字段
            "buy1_depth": self.bid_depth_1,
            "sell1_depth": self.ask_depth_1,
        }


@dataclass
class ActiveQuote:
    quote_id: str
    pair: str
    side: str  # bid / ask
    quote_price: float
    created_ts: float
    reason: str = ""
    trade_id: Optional[int] = None
    status: str = "open"  # open / filled / canceled


@dataclass
class PendingFillPath:
    fill_id: str
    pair: str
    side: str
    fill_price: float
    fill_ts: float
    quote_id: Optional[str] = None
    exit_reason: Optional[str] = None
    # horizon prices: +1s +5s +10s +30s +60s +300s
    after_1s_price: Optional[float] = None
    after_5s_price: Optional[float] = None
    after_10s_price: Optional[float] = None
    after_30s_price: Optional[float] = None
    after_1m_price: Optional[float] = None
    after_5m_price: Optional[float] = None
    # running extrema
    min_price: float = 0.0
    max_price: float = 0.0
    # time-MAE / MFE at horizons
    mae_1s: Optional[float] = None
    mae_5s: Optional[float] = None
    mae_10s: Optional[float] = None
    mae_30s: Optional[float] = None
    mae_1m: Optional[float] = None
    mae_5m: Optional[float] = None
    mfe_1s: Optional[float] = None
    mfe_5s: Optional[float] = None
    mfe_10s: Optional[float] = None
    mfe_30s: Optional[float] = None
    mfe_1m: Optional[float] = None
    mfe_5m: Optional[float] = None
    done: bool = False

    def __post_init__(self):
        self.min_price = self.fill_price
        self.max_price = self.fill_price

    def signed_excursions(self) -> tuple[float, float]:
        """Return (mae, mfe) at current min/max. mae<=0 adverse, mfe>=0 favorable."""
        if self.side == "long":
            mae = (self.min_price - self.fill_price) / self.fill_price
            mfe = (self.max_price - self.fill_price) / self.fill_price
        else:
            mae = (self.fill_price - self.max_price) / self.fill_price
            mfe = (self.fill_price - self.min_price) / self.fill_price
        return mae, mfe

    def fav_ret_at(self, px: Optional[float]) -> Optional[float]:
        if px is None or self.fill_price <= 0:
            return None
        raw = (px - self.fill_price) / self.fill_price
        return raw if self.side == "long" else -raw


def classify_path_type(p: "PendingFillPath") -> str:
    """
    成交后路径形态（决定未来 Quote Logic）：
      A_immediate_edge  — 立即有利（1s/5s 已正，30s 仍正）
      B_drawdown_then_recover — 先亏后赚（早期 MAE，末期有利）
      C_toxic           — 成交即错误（持续不利）
      D_mixed           — 其它
    """
    r1 = p.fav_ret_at(p.after_1s_price)
    r5 = p.fav_ret_at(p.after_5s_price)
    r30 = p.fav_ret_at(p.after_30s_price)
    r300 = p.fav_ret_at(p.after_5m_price)
    mae30 = p.mae_30s or 0.0

    if r30 is not None and r30 > 0 and (r1 or 0) >= 0 and (r5 or 0) >= 0:
        return "A_immediate_edge"
    if mae30 < -1e-6 and r300 is not None and r300 > 0:
        return "B_drawdown_then_recover"
    if r30 is not None and r30 < 0 and (r300 is None or r300 <= 0):
        return "C_toxic"
    return "D_mixed"


class MakerEdgeLogger:
    def __init__(
        self,
        log_dir: str | Path | None = None,
        levels: int = 10,
        book_history_sec: float = 30.0,
        cluster_gap_sec: float = 30.0,
        mid_tick_every_sec: float = 1.0,
    ):
        # .../nautilus_mm/src/nautilus_mm/recorder.py → parents[2] = nautilus_mm
        root = Path(__file__).resolve().parents[2]
        self.log_dir = Path(log_dir) if log_dir else root / "logs" / "maker_edge"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.levels = levels
        self.book_history_sec = book_history_sec
        self.cluster_gap_sec = cluster_gap_sec
        self.mid_tick_every_sec = mid_tick_every_sec
        self._pending: dict[str, PendingFillPath] = {}
        self._quotes: dict[str, ActiveQuote] = {}  # quote_id -> ActiveQuote
        self._quotes_by_trade: dict[int, str] = {}  # trade_id -> quote_id
        self._book_hist: deque[tuple[float, MicroSnapshot]] = deque(maxlen=2000)
        # inventory tracking for future quote engine
        self._inv: float = 0.0
        self._inv_nonzero_since: Optional[float] = None
        self._inv_target: float = 0.0  # flat target; skew = inv - target
        # liquidity-event clustering (样本独立性)
        self._cluster_id: Optional[str] = None
        self._cluster_side: Optional[str] = None
        self._cluster_last_ts: float = 0.0
        self._cluster_start_mid: Optional[float] = None
        self._cluster_n: int = 0
        self._last_mid_tick_ts: float = 0.0
        self.experiment = load_experiment_meta()

    def _file(self) -> Path:
        return self.log_dir / f"{_utc_now().strftime('%Y%m%d')}.jsonl"

    def update_inventory(self, inventory: float, now: float | None = None) -> dict:
        """更新库存并返回 inventory / inventory_time / inventory_skew。"""
        now = now or time.time()
        self._inv = float(inventory)
        if abs(self._inv) < 1e-12:
            self._inv_nonzero_since = None
            inv_time = 0.0
        else:
            if self._inv_nonzero_since is None:
                self._inv_nonzero_since = now
            inv_time = now - self._inv_nonzero_since
        skew = self._inv - self._inv_target
        return {
            "inventory": self._inv,
            "inventory_time": inv_time,
            "inventory_skew": skew,
        }

    def _attach_common(
        self,
        ev: dict[str, Any],
        inventory: float | None = None,
        state: dict | None = None,
        now: float | None = None,
    ) -> dict[str, Any]:
        now = now or time.time()
        if inventory is not None:
            ev.update(self.update_inventory(inventory, now=now))
        # 始终带 market_state_snapshot（可被 state 覆盖内部字段）
        mss = empty_market_state_snapshot()
        if state:
            for k in mss:
                if k in state and state[k] is not None:
                    mss[k] = state[k]
            # 兼容旧扁平字段
            for k, v in state.items():
                if k not in mss and k != "market_state_snapshot":
                    ev.setdefault(k, v)
        ev["market_state_snapshot"] = mss
        return ev

    def write(self, event: dict[str, Any]) -> None:
        event.setdefault("ts", _iso())
        event.setdefault("ts_epoch", time.time())
        if "market_state_snapshot" not in event:
            event["market_state_snapshot"] = empty_market_state_snapshot()
        stamp_event(event, self.experiment)
        with self._file().open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def write_experiment_start(self, extra: dict | None = None) -> None:
        """探针启动时写入一次，绑定本轮 Data Collection。"""
        ev = {
            "event": "experiment_start",
            **self.experiment,
        }
        if extra:
            ev.update(extra)
        self.write(ev)

    # ------------------------------------------------------------------ #
    # Snapshot
    # ------------------------------------------------------------------ #
    @staticmethod
    def snapshot_from_orderbook(
        ob: dict,
        levels: int = 10,
        recent_trades: list | None = None,
        last_mid: float | None = None,
        liq_proxy_low: float | None = None,
        liq_proxy_high: float | None = None,
    ) -> MicroSnapshot:
        bids = (ob.get("bids") or [])[:levels]
        asks = (ob.get("asks") or [])[:levels]
        if not bids or not asks:
            return MicroSnapshot()

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid = (best_bid + best_ask) / 2.0
        spread = best_ask - best_bid

        def depth(levels_side, n):
            return sum(float(x[1]) for x in levels_side[:n])

        bid_depth_1 = depth(bids, 1)
        ask_depth_1 = depth(asks, 1)
        bid_depth_5 = depth(bids, 5)
        ask_depth_5 = depth(asks, 5)
        bid_depth = depth(bids, levels)
        ask_depth = depth(asks, levels)
        tot = bid_depth + ask_depth
        obi = ((bid_depth - ask_depth) / tot) if tot > 0 else 0.0

        buy_v = sell_v = 0.0
        if recent_trades:
            for t in recent_trades:
                amt = float(t.get("amount") or t.get("qty") or 0.0)
                side = (t.get("side") or "").lower()
                if side in ("buy", "b"):
                    buy_v += amt
                elif side in ("sell", "s"):
                    sell_v += amt
        delta = buy_v - sell_v
        timb_den = buy_v + sell_v
        trade_imbalance = ((buy_v - sell_v) / timb_den) if timb_den > 0 else 0.0

        de = 0.0
        if last_mid and mid and abs(delta) > 1e-12:
            de = ((mid - last_mid) / last_mid) / delta

        liq_dist = 0.0
        if liq_proxy_low and liq_proxy_high and mid:
            rng = liq_proxy_high - liq_proxy_low
            if rng > 0:
                liq_dist = ((mid - liq_proxy_low) / rng) * 2 - 1

        return MicroSnapshot(
            best_bid=best_bid,
            best_ask=best_ask,
            mid=mid,
            spread=spread,
            bid_depth_1=bid_depth_1,
            ask_depth_1=ask_depth_1,
            bid_depth_5=bid_depth_5,
            ask_depth_5=ask_depth_5,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            obi=obi,
            delta=delta,
            trade_imbalance=trade_imbalance,
            delta_efficiency=de,
            liquidation_distance=liq_dist,
        )

    def record_book(
        self,
        snap: MicroSnapshot,
        now: float | None = None,
        *,
        emit_mid_tick: bool = True,
        pair: str | None = None,
    ) -> None:
        now = now or time.time()
        self._book_hist.append((now, snap))
        # trim old
        cutoff = now - self.book_history_sec
        while self._book_hist and self._book_hist[0][0] < cutoff:
            self._book_hist.popleft()
        # mid 时间序列：供 Fill vs Random Benchmark（研究保护栏）
        if (
            emit_mid_tick
            and snap.mid > 0
            and (now - self._last_mid_tick_ts) >= self.mid_tick_every_sec
        ):
            self._last_mid_tick_ts = now
            self.write(
                {
                    "event": "mid_tick",
                    "pair": pair,
                    "mid": snap.mid,
                    "best_bid": snap.best_bid,
                    "best_ask": snap.best_ask,
                    "spread": snap.spread,
                    "ts_epoch": now,
                }
            )

    def assign_event_cluster(
        self,
        side: str,
        mid: float,
        now: float | None = None,
    ) -> dict[str, Any]:
        """
        将连续同侧成交归入同一流动性事件（event_cluster_id）。

        规则（研究保护栏，非策略）：
        - 同 side
        - 与上一笔间隔 < cluster_gap_sec
        → 同一 cluster；否则新开 cluster。

        统计时应用 cluster 加权，避免「暴跌连续 50 笔 Bid」当成 50 个独立样本。
        """
        now = now or time.time()
        new_cluster = (
            self._cluster_id is None
            or self._cluster_side != side
            or (now - self._cluster_last_ts) > self.cluster_gap_sec
        )
        if new_cluster:
            self._cluster_id = uuid.uuid4().hex[:12]
            self._cluster_side = side
            self._cluster_start_mid = mid if mid > 0 else None
            self._cluster_n = 0
        self._cluster_n += 1
        self._cluster_last_ts = now
        mid_move = None
        if self._cluster_start_mid and mid > 0:
            mid_move = (mid - self._cluster_start_mid) / self._cluster_start_mid
        return {
            "event_cluster_id": self._cluster_id,
            "cluster_fill_index": self._cluster_n,
            "cluster_mid_move_from_start": mid_move,
        }

    def book_at(self, target_ts: float) -> Optional[MicroSnapshot]:
        """取最接近 target_ts 的历史盘口（用于成交前5s）。"""
        if not self._book_hist:
            return None
        best = min(self._book_hist, key=lambda x: abs(x[0] - target_ts))
        return best[1]

    def build_fill_context(self, side: str, now: float | None = None) -> dict:
        """
        成交主动性上下文：区分「砸盘后吸收」vs「下跌接刀」。
        不接 Market Pulse，仅用本地 book history + trade imbalance。
        """
        now = now or time.time()
        cur = self.book_at(now)
        past = self.book_at(now - 5.0)
        fill_type = "bid" if side == "long" else "ask"
        ctx: dict[str, Any] = {
            "fill_type": fill_type,
            "market_event_before_fill": "unknown",
            "trade_imbalance_5s": None,
            "price_velocity_5s": None,
        }
        if not cur or not past or past.mid <= 0:
            return {"fill_context": ctx}

        vel = (cur.mid - past.mid) / past.mid
        # 用当前与 5s 前 imbalance 的平均作代理
        timb = (cur.trade_imbalance + past.trade_imbalance) / 2.0
        ctx["trade_imbalance_5s"] = timb
        ctx["price_velocity_5s"] = vel

        if fill_type == "bid":
            # 卖压后吸收：价格下行/企稳 + 卖向 imbalance，但盘口未继续恶化太狠
            if timb < -0.2 and vel < 0:
                if abs(vel) < 0.0003:
                    ctx["market_event_before_fill"] = "sell_pressure_absorbing"
                else:
                    ctx["market_event_before_fill"] = "sell_pressure_falling"
            elif vel < -0.0005:
                ctx["market_event_before_fill"] = "momentum_down_catching_knife"
            elif timb > 0.15:
                ctx["market_event_before_fill"] = "buy_support"
            else:
                ctx["market_event_before_fill"] = "neutral"
        else:
            if timb > 0.2 and vel > 0:
                if abs(vel) < 0.0003:
                    ctx["market_event_before_fill"] = "buy_pressure_absorbing"
                else:
                    ctx["market_event_before_fill"] = "buy_pressure_rising"
            elif vel > 0.0005:
                ctx["market_event_before_fill"] = "momentum_up_chasing"
            elif timb < -0.15:
                ctx["market_event_before_fill"] = "sell_resistance"
            else:
                ctx["market_event_before_fill"] = "neutral"
        return {"fill_context": ctx}

    def book_deterioration(self, side: str, now: float | None = None, lookback: float = 5.0) -> dict:
        """
        成交前 lookback 秒盘口是否恶化。
        long: bid_depth 下降 / ask_depth 上升 / mid 下跌 → 恶化
        """
        now = now or time.time()
        cur = self.book_at(now)
        past = self.book_at(now - lookback)
        if not cur or not past or past.mid <= 0:
            return {"book_ok": False}
        mid_chg = (cur.mid - past.mid) / past.mid
        bid5_chg = (cur.bid_depth_5 - past.bid_depth_5) / past.bid_depth_5 if past.bid_depth_5 else 0.0
        ask5_chg = (cur.ask_depth_5 - past.ask_depth_5) / past.ask_depth_5 if past.ask_depth_5 else 0.0
        obi_chg = cur.obi - past.obi
        if side == "long":
            deteriorated = (mid_chg < -0.00005) or (bid5_chg < -0.15) or (obi_chg < -0.1)
        else:
            deteriorated = (mid_chg > 0.00005) or (ask5_chg < -0.15) or (obi_chg > 0.1)
        return {
            "book_ok": True,
            "pre_5s_mid_chg": mid_chg,
            "pre_5s_bid_depth_5_chg": bid5_chg,
            "pre_5s_ask_depth_5_chg": ask5_chg,
            "pre_5s_obi_chg": obi_chg,
            "pre_5s_deteriorated": bool(deteriorated),
            "pre_5s_bid_depth_1": past.bid_depth_1,
            "pre_5s_ask_depth_1": past.ask_depth_1,
            "pre_5s_bid_depth_5": past.bid_depth_5,
            "pre_5s_ask_depth_5": past.ask_depth_5,
            "pre_5s_obi": past.obi,
            "pre_5s_spread": past.spread,
            "pre_5s_trade_imbalance": past.trade_imbalance,
        }

    # ------------------------------------------------------------------ #
    # Quote lifecycle
    # ------------------------------------------------------------------ #
    def create_quote(
        self,
        pair: str,
        side: str,
        quote_price: float,
        inventory: float,
        snap: MicroSnapshot,
        reason: str = "",
        trade_id: Optional[int] = None,
        state: dict | None = None,
        extra: dict | None = None,
    ) -> str:
        qid = uuid.uuid4().hex[:16]
        now = time.time()
        q = ActiveQuote(
            quote_id=qid,
            pair=pair,
            side=side,
            quote_price=quote_price,
            created_ts=now,
            reason=reason,
            trade_id=trade_id,
            status="open",
        )
        self._quotes[qid] = q
        if trade_id is not None:
            self._quotes_by_trade[trade_id] = qid

        ev = {
            "event": "quote_created",
            "quote_id": qid,
            "pair": pair,
            "side": side,
            "quote_price": quote_price,
            "quote_created_time": _iso(now),
            "quote_created_epoch": now,
            "reason": reason,
            "trade_id": trade_id,
            "status": "open",
            "filled": False,
        }
        ev.update(snap.to_book_fields())
        self._attach_common(ev, inventory=inventory, state=state, now=now)
        if extra:
            ev.update(extra)
        self.write(ev)
        return qid

    def cancel_quote(
        self,
        quote_id: str | None = None,
        trade_id: Optional[int] = None,
        reason: str = "timeout",
        snap: MicroSnapshot | None = None,
    ) -> None:
        q = None
        if quote_id and quote_id in self._quotes:
            q = self._quotes[quote_id]
        elif trade_id is not None and trade_id in self._quotes_by_trade:
            q = self._quotes.get(self._quotes_by_trade[trade_id])
        if q is None or q.status != "open":
            return

        now = time.time()
        q.status = "canceled"
        ev = {
            "event": "quote_canceled",
            "quote_id": q.quote_id,
            "pair": q.pair,
            "side": q.side,
            "quote_price": q.quote_price,
            "quote_created_time": _iso(q.created_ts),
            "quote_cancel_time": _iso(now),
            "quote_cancel_epoch": now,
            "time_alive_sec": now - q.created_ts,
            "cancel_reason": reason,
            "filled": False,
            "status": "canceled",
            "trade_id": q.trade_id,
        }
        if snap:
            ev.update(snap.to_book_fields())
        self.write(ev)

    def bind_trade(self, quote_id: str, trade_id: int) -> None:
        if quote_id in self._quotes:
            self._quotes[quote_id].trade_id = trade_id
            self._quotes_by_trade[trade_id] = quote_id

    # ------------------------------------------------------------------ #
    # Fill + path
    # ------------------------------------------------------------------ #
    def log_fill(
        self,
        pair: str,
        side: str,
        fill_price: float,
        amount: float,
        inventory: float,
        snap: MicroSnapshot | None,
        order_type: str = "limit",
        quote_id: str | None = None,
        trade_id: Optional[int] = None,
        fill_reason: str = "maker_hit",
        state: dict | None = None,
        extra: dict | None = None,
        quote_terminal: bool = True,
    ) -> str:
        """Record a fill. Always writes even if snap is None (book unavailable).

        quote_terminal=False keeps quote open for partial fills so later slices
        retain quote_id linkage until the order closes.
        """
        now = time.time()
        fill_id = uuid.uuid4().hex[:16]
        snap = snap or MicroSnapshot()

        # resolve quote lifecycle
        q: Optional[ActiveQuote] = None
        if quote_id and quote_id in self._quotes:
            q = self._quotes[quote_id]
        elif trade_id is not None and trade_id in self._quotes_by_trade:
            q = self._quotes.get(self._quotes_by_trade[trade_id])

        time_to_fill = None
        quote_created_time = None
        quote_price = fill_price
        if q is not None:
            if quote_terminal:
                q.status = "filled"
            time_to_fill = now - q.created_ts
            quote_created_time = _iso(q.created_ts)
            quote_price = q.quote_price
            quote_id = q.quote_id

        det = self.book_deterioration(side, now=now, lookback=5.0)
        fctx = self.build_fill_context(side, now=now)
        mid_for_cluster = snap.mid if snap.mid > 0 else fill_price
        cluster = self.assign_event_cluster(side, mid_for_cluster, now=now)

        ev = {
            "event": "fill",
            "fill_id": fill_id,
            "quote_id": quote_id,
            "pair": pair,
            "side": side,
            "fill_price": fill_price,
            "quote_price": quote_price,
            "amount": amount,
            "order_type": order_type,
            "fill_reason": fill_reason,
            "quote_created_time": quote_created_time,
            "quote_fill_time": _iso(now),
            "time_to_fill": time_to_fill,
            "trade_id": trade_id,
            "filled": True,
            "quote_terminal": quote_terminal,
            "book_available": bool(snap.mid > 0),
        }
        ev.update(snap.to_book_fields())
        ev.update(det)
        ev.update(fctx)
        ev.update(cluster)
        # Effective spread capture proxy: 相对 mid 的被动成交优势
        if snap.mid > 0:
            if side == "long":
                ev["spread_capture_pct"] = (snap.mid - fill_price) / snap.mid
            else:
                ev["spread_capture_pct"] = (fill_price - snap.mid) / snap.mid
        self._attach_common(ev, inventory=inventory, state=state, now=now)
        if extra:
            ev.update(extra)
        self.write(ev)

        # also emit quote_filled lifecycle event (only when order fully done)
        if q is not None and quote_terminal:
            self.write(
                {
                    "event": "quote_filled",
                    "quote_id": q.quote_id,
                    "fill_id": fill_id,
                    "pair": pair,
                    "side": q.side,
                    "quote_price": q.quote_price,
                    "quote_created_time": _iso(q.created_ts),
                    "quote_fill_time": _iso(now),
                    "time_to_fill": time_to_fill,
                    "fill_reason": fill_reason,
                    "filled": True,
                    "status": "filled",
                    "trade_id": trade_id,
                    **snap.to_book_fields(),
                    **det,
                }
            )

        self._pending[fill_id] = PendingFillPath(
            fill_id=fill_id,
            pair=pair,
            side=side,
            fill_price=fill_price,
            fill_ts=now,
            quote_id=quote_id,
        )
        return fill_id

    def attach_exit_reason(self, fill_id: str, exit_reason: str) -> None:
        if fill_id in self._pending:
            self._pending[fill_id].exit_reason = exit_reason
        # also write lightweight annotation
        self.write(
            {
                "event": "fill_exit",
                "fill_id": fill_id,
                "exit_reason": exit_reason,
            }
        )

    def update_paths(self, pair: str, last_price: float, now: float | None = None) -> None:
        now = now or time.time()
        finished = []
        for fid, p in self._pending.items():
            if p.pair != pair or p.done:
                continue
            p.min_price = min(p.min_price, last_price)
            p.max_price = max(p.max_price, last_price)
            mae, mfe = p.signed_excursions()
            age = now - p.fill_ts

            def mark(horizon_attr_price, horizon_mae, horizon_mfe, sec, price_val):
                if getattr(p, horizon_attr_price) is None and age >= sec:
                    setattr(p, horizon_attr_price, price_val)
                    setattr(p, horizon_mae, mae)
                    setattr(p, horizon_mfe, mfe)

            mark("after_1s_price", "mae_1s", "mfe_1s", 1, last_price)
            mark("after_5s_price", "mae_5s", "mfe_5s", 5, last_price)
            mark("after_10s_price", "mae_10s", "mfe_10s", 10, last_price)
            mark("after_30s_price", "mae_30s", "mfe_30s", 30, last_price)
            mark("after_1m_price", "mae_1m", "mfe_1m", 60, last_price)

            if p.after_5m_price is None and age >= 300:
                p.after_5m_price = last_price
                p.mae_5m = mae
                p.mfe_5m = mfe
                p.done = True
                # Price MAE absolute
                if p.side == "long":
                    price_mae = p.min_price - p.fill_price
                    price_mfe = p.max_price - p.fill_price
                else:
                    price_mae = p.fill_price - p.max_price
                    price_mfe = p.fill_price - p.min_price

                fav_30 = p.fav_ret_at(p.after_30s_price) or 0.0
                fav_1 = p.fav_ret_at(p.after_1s_price)
                fav_5 = p.fav_ret_at(p.after_5s_price)
                fav_10 = p.fav_ret_at(p.after_10s_price)
                fav_60 = p.fav_ret_at(p.after_1m_price)
                fav_300 = p.fav_ret_at(p.after_5m_price) or 0.0

                vol_proxy = abs(p.max_price - p.min_price) / p.fill_price if p.fill_price else 0.0
                toxicity_score = max(0.0, -fav_30) / max(vol_proxy, 1e-8)
                mfe_gt_mae_30 = (p.mfe_30s or 0.0) > abs(p.mae_30s or 0.0)
                path_type = classify_path_type(p)

                # 路径点（供形态分析 / 复现）
                price_path = {
                    "t0": p.fill_price,
                    "t1s": p.after_1s_price,
                    "t5s": p.after_5s_price,
                    "t10s": p.after_10s_price,
                    "t30s": p.after_30s_price,
                    "t60s": p.after_1m_price,
                    "t300s": p.after_5m_price,
                }
                ret_path = {
                    "t1s": fav_1,
                    "t5s": fav_5,
                    "t10s": fav_10,
                    "t30s": fav_30,
                    "t60s": fav_60,
                    "t300s": fav_300,
                }

                self.write(
                    {
                        "event": "fill_path",
                        "fill_id": p.fill_id,
                        "quote_id": p.quote_id,
                        "pair": p.pair,
                        "side": p.side,
                        "fill_price": p.fill_price,
                        "exit_reason": p.exit_reason,
                        "after_1s_price": p.after_1s_price,
                        "after_5s_price": p.after_5s_price,
                        "after_10s_price": p.after_10s_price,
                        "after_30s_price": p.after_30s_price,
                        "after_1m_price": p.after_1m_price,
                        "after_5m_price": p.after_5m_price,
                        "price_path": price_path,
                        "ret_path": ret_path,
                        "path_type": path_type,
                        "min_price": p.min_price,
                        "max_price": p.max_price,
                        "mae_1s": p.mae_1s,
                        "mae_5s": p.mae_5s,
                        "mae_10s": p.mae_10s,
                        "mae_30s": p.mae_30s,
                        "mae_1m": p.mae_1m,
                        "mae_5m": p.mae_5m,
                        "mfe_1s": p.mfe_1s,
                        "mfe_5s": p.mfe_5s,
                        "mfe_10s": p.mfe_10s,
                        "mfe_30s": p.mfe_30s,
                        "mfe_1m": p.mfe_1m,
                        "mfe_5m": p.mfe_5m,
                        "price_mae": price_mae,
                        "price_mfe": price_mfe,
                        "price_mae_pct": mae,
                        "price_mfe_pct": mfe,
                        "fav_ret_30s": fav_30,
                        "vol_proxy_5m": vol_proxy,
                        "toxicity_score": toxicity_score,
                        "mfe_gt_mae_30s": mfe_gt_mae_30,
                    }
                )
                finished.append(fid)

        for fid in finished:
            self._pending.pop(fid, None)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    # 兼容旧 API
    def log_quote(self, *args, **kwargs):
        """Deprecated wrapper → create_quote for live quotes; heartbeat uses book only."""
        return self.create_quote(*args, **kwargs)
