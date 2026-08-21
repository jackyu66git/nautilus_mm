"""
Immutable Event Ledger — MM_EDGE_EXP_002

Raw Event > Derived Feature

Stores immutable market events for later reconstruction of pre-fill windows.
Features are computed offline; this module only persists observability data.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nautilus_mm.experiment import load_experiment_meta, stamp_event
from nautilus_mm.recorder import MicroSnapshot

LEDGER_SCHEMA_VERSION = "immutable_event_v1"


def _git_commit(root: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if r.returncode == 0:
            return r.stdout.strip() or None
    except Exception:
        return None
    return None


def load_run_identity(*, extra_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Freeze one Ledger Integrity ID per collection run (sessions share the same run_id)."""
    root = Path(__file__).resolve().parents[2]
    cfg = {
        "prefill_window_sec": os.getenv("PREFILL_WINDOW_SEC", "5.0"),
        "prefill_margin_sec": os.getenv("PREFILL_MARGIN_SEC", "0.25"),
        "large_trade_qty": os.getenv("LARGE_TRADE_QTY", "0.1"),
        "book_depth": os.getenv("BOOK_DEPTH", "10"),
        "symbol": os.getenv("SYMBOL", "BTCUSDT-PERP"),
        "environment": os.getenv("BINANCE_ENVIRONMENT", "TESTNET"),
        "schema_version": LEDGER_SCHEMA_VERSION,
    }
    if extra_config:
        cfg.update({k: str(v) for k, v in extra_config.items()})
    payload = json.dumps(cfg, sort_keys=True, default=str)
    return {
        "run_id": os.getenv("LEDGER_RUN_ID", "EXP-002-RUN-UNSET"),
        "session_id": os.getenv("LEDGER_SESSION_ID") or uuid.uuid4().hex[:12],
        "schema_version": LEDGER_SCHEMA_VERSION,
        "host": socket.gethostname(),
        "commit": _git_commit(root),
        "config_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16],
        "config_snapshot": cfg,
    }


def _utc_iso(ts: float | None = None) -> str:
    t = datetime.fromtimestamp(ts or time.time(), tz=timezone.utc)
    return t.isoformat()


@dataclass
class EventTimingState:
    last_trade_ts: float | None = None
    last_large_trade_ts: float | None = None
    last_book_event_ts: float | None = None
    last_tob_change_ts: float | None = None
    last_spread_change_ts: float | None = None
    last_mid_change_ts: float | None = None
    last_depth_change_ts: float | None = None


class ImmutableEventLedger:
    """Append-only JSONL ledger for market events."""

    def __init__(
        self,
        log_dir: str | Path | None = None,
        *,
        prefill_window_sec: float = 5.0,
        prefill_margin_sec: float = 0.25,
        large_trade_qty: float = 0.1,
        book_levels: int = 10,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.log_dir = Path(log_dir) if log_dir else root / "logs" / "event_state"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.prefill_window_sec = float(prefill_window_sec)
        self.prefill_margin_sec = float(prefill_margin_sec)
        self.large_trade_qty = float(large_trade_qty)
        self.book_levels = int(book_levels)
        self.experiment = load_experiment_meta()
        self.run_identity = load_run_identity(
            extra_config={
                "prefill_window_sec": self.prefill_window_sec,
                "prefill_margin_sec": self.prefill_margin_sec,
                "large_trade_qty": self.large_trade_qty,
                "book_levels": self.book_levels,
            }
        )
        self._timing = EventTimingState()
        self._prev_snap: MicroSnapshot | None = None
        self._event_seq = 0
        self._session_event_count = 0

    def _file(self) -> Path:
        return self.log_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"

    def _next_seq(self) -> int:
        self._event_seq += 1
        return self._event_seq

    def _timing_fields(self, now: float, *, is_trade: bool = False, is_large_trade: bool = False) -> dict[str, Any]:
        def _since(last: float | None) -> float | None:
            if last is None:
                return None
            return (now - last) * 1000.0

        fields = {
            "time_since_last_trade_ms": _since(self._timing.last_trade_ts),
            "time_since_last_large_trade_ms": _since(self._timing.last_large_trade_ts),
            "time_since_last_book_event_ms": _since(self._timing.last_book_event_ts),
            "time_since_last_tob_change_ms": _since(self._timing.last_tob_change_ts),
            "time_since_last_spread_change_ms": _since(self._timing.last_spread_change_ts),
            "time_since_last_mid_change_ms": _since(self._timing.last_mid_change_ts),
            "time_since_last_depth_change_ms": _since(self._timing.last_depth_change_ts),
        }
        self._timing.last_book_event_ts = now
        if is_trade:
            self._timing.last_trade_ts = now
            if is_large_trade:
                self._timing.last_large_trade_ts = now
        return fields

    def write(self, event: dict[str, Any]) -> None:
        # Receive time is always local wall clock. Never copy exchange_ts into local_ts.
        now = time.time()
        now_ns = time.time_ns()
        event["ledger"] = LEDGER_SCHEMA_VERSION
        event["schema_version"] = LEDGER_SCHEMA_VERSION
        event["run_id"] = self.run_identity["run_id"]
        event["session_id"] = self.run_identity["session_id"]
        event["local_ts_epoch"] = now
        event["local_ts_ns"] = now_ns
        event["local_ts"] = _utc_iso(now)
        event["event_seq"] = self._next_seq()
        self._session_event_count += 1
        stamp_event(event, self.experiment)
        with self._file().open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            f.flush()

    def write_experiment_start(self, extra: dict | None = None) -> None:
        ev = {
            "event": "experiment_start",
            "experiment_type": "Event-State Observability Probe",
            "strategy": "NONE",
            "execution_trading": False,
            "prefill_window_sec": self.prefill_window_sec,
            "prefill_margin_sec": self.prefill_margin_sec,
            "large_trade_qty": self.large_trade_qty,
            **self.experiment,
            **{k: v for k, v in self.run_identity.items() if k != "config_snapshot"},
            "config_snapshot": self.run_identity["config_snapshot"],
        }
        if extra:
            ev.update(extra)
        self.write(ev)

    def write_experiment_stop(self, extra: dict | None = None) -> None:
        ev = {
            "event": "experiment_stop",
            "session_event_count": self._session_event_count,
            "run_id": self.run_identity["run_id"],
            "session_id": self.run_identity["session_id"],
            "execution_trading": False,
        }
        if extra:
            ev.update(extra)
        self.write(ev)

    def log_aggressive_trade(
        self,
        *,
        pair: str,
        price: float,
        qty: float,
        trade_side: str,
        exchange_ts_ns: int | None,
        local_ts_epoch: float | None = None,
        aggressor_side: str | None = None,
        trade_id: str | None = None,
        snap: MicroSnapshot | None = None,
    ) -> str:
        now = local_ts_epoch or time.time()
        notional = price * qty
        is_large = qty >= self.large_trade_qty
        event_id = uuid.uuid4().hex[:16]
        ev = {
            "event": "market_event",
            "event_id": event_id,
            "event_type": "aggressive_trade",
            "pair": pair,
            "price": price,
            "quantity": qty,
            "trade_qty": qty,
            "trade_price": price,
            "trade_notional": notional,
            "trade_side": trade_side,
            "aggressor_side": aggressor_side or trade_side,
            "large_trade_flag": is_large,
            "trade_id": trade_id,
            "exchange_ts_ns": exchange_ts_ns,
        }
        if snap is not None:
            ev.update(self._snap_book_fields(snap))
            ev.update(self._depth_deltas(self._prev_snap, snap))
        ev.update(self._timing_fields(now, is_trade=True, is_large_trade=is_large))
        self.write(ev)
        return event_id

    def _snap_book_fields(self, snap: MicroSnapshot) -> dict[str, Any]:
        return {
            "best_bid": snap.best_bid,
            "best_ask": snap.best_ask,
            "mid": snap.mid,
            "spread": snap.spread,
            "bid_depth_1": snap.bid_depth_1,
            "ask_depth_1": snap.ask_depth_1,
            "bid_depth_5": snap.bid_depth_5,
            "ask_depth_5": snap.ask_depth_5,
            "bid_depth": snap.bid_depth,
            "ask_depth": snap.ask_depth,
            "obi": snap.obi,
        }

    def _depth_deltas(self, prev: MicroSnapshot | None, cur: MicroSnapshot) -> dict[str, Any]:
        if prev is None:
            return {
                "bid_depth_delta_1": None,
                "ask_depth_delta_1": None,
                "bid_depth_delta_5": None,
                "ask_depth_delta_5": None,
                "bid_depth_delta": None,
                "ask_depth_delta": None,
            }
        return {
            "bid_depth_delta_1": cur.bid_depth_1 - prev.bid_depth_1,
            "ask_depth_delta_1": cur.ask_depth_1 - prev.ask_depth_1,
            "bid_depth_delta_5": cur.bid_depth_5 - prev.bid_depth_5,
            "ask_depth_delta_5": cur.ask_depth_5 - prev.ask_depth_5,
            "bid_depth_delta": cur.bid_depth - prev.bid_depth,
            "ask_depth_delta": cur.ask_depth - prev.ask_depth,
        }

    def log_book_state(
        self,
        *,
        pair: str,
        snap: MicroSnapshot,
        exchange_ts_ns: int | None,
        local_ts_epoch: float | None = None,
        sequence: int | None = None,
        delta_count: int | None = None,
        event_type: str = "book_update",
    ) -> str:
        now = local_ts_epoch or time.time()
        prev = self._prev_snap
        event_id = uuid.uuid4().hex[:16]

        bid_move = None
        ask_move = None
        mid_move = None
        spread_change = None
        if prev and prev.mid > 0:
            bid_move = snap.best_bid - prev.best_bid
            ask_move = snap.best_ask - prev.best_ask
            mid_move = snap.mid - prev.mid
            spread_change = snap.spread - prev.spread

        depth_deltas = self._depth_deltas(prev, snap)
        ev = {
            "event": "market_event",
            "event_id": event_id,
            "event_type": event_type,
            "pair": pair,
            "exchange_ts_ns": exchange_ts_ns,
            "sequence": sequence,
            "delta_count": delta_count,
            **self._snap_book_fields(snap),
            **depth_deltas,
            "bid_move": bid_move,
            "ask_move": ask_move,
            "mid_move": mid_move,
            "spread_change": spread_change,
        }
        ev.update(self._timing_fields(now))

        if prev is not None:
            if bid_move not in (None, 0.0) or ask_move not in (None, 0.0):
                self._timing.last_tob_change_ts = now
            if spread_change not in (None, 0.0):
                self._timing.last_spread_change_ts = now
            if mid_move not in (None, 0.0):
                self._timing.last_mid_change_ts = now
            if any(
                depth_deltas[k] not in (None, 0.0)
                for k in (
                    "bid_depth_delta_1",
                    "ask_depth_delta_1",
                    "bid_depth_delta_5",
                    "ask_depth_delta_5",
                )
            ):
                self._timing.last_depth_change_ts = now

        self._prev_snap = snap
        self.write(ev)
        return event_id

    def log_fill_anchor(
        self,
        *,
        fill_id: str,
        fill_ts_epoch: float,
        exchange_ts_ns: int | None,
        side: str,
        fill_price: float,
        fill_qty: float,
        order_id: str | None = None,
        venue_order_id: str | None = None,
        venue_trade_id: str | None = None,
        pair: str | None = None,
        snap: MicroSnapshot | None = None,
        extra: dict | None = None,
    ) -> str:
        """
        Anchor for offline [-prefill_window_sec, fill) reconstruction.

        EXP_002 Phase 1 may not emit these (no trading). Schema is frozen for
        future fill-anchored analysis (Gate 4).
        """
        window_id = uuid.uuid4().hex[:16]
        window_start = fill_ts_epoch - self.prefill_window_sec
        feature_cutoff = fill_ts_epoch - self.prefill_margin_sec
        ev = {
            "event": "fill_anchor",
            "window_id": window_id,
            "fill_id": fill_id,
            "fill_ts_epoch": fill_ts_epoch,
            "fill_ts": _utc_iso(fill_ts_epoch),
            "exchange_ts_ns": exchange_ts_ns,
            "window_start_epoch": window_start,
            "feature_cutoff_epoch": feature_cutoff,
            "prefill_window_sec": self.prefill_window_sec,
            "prefill_margin_sec": self.prefill_margin_sec,
            "side": side,
            "fill_price": fill_price,
            "fill_qty": fill_qty,
            "order_id": order_id,
            "venue_order_id": venue_order_id,
            "venue_trade_id": venue_trade_id,
            "pair": pair,
        }
        if snap is not None:
            ev.update(self._snap_book_fields(snap))
        if extra:
            ev.update(extra)
        self.write(ev)
        return window_id

    def events_in_window(self, events: list[dict], fill_ts_epoch: float) -> list[dict]:
        """Offline helper: filter market_event rows in [-window, fill-margin)."""
        start = fill_ts_epoch - self.prefill_window_sec
        cutoff = fill_ts_epoch - self.prefill_margin_sec
        out = []
        for ev in events:
            if ev.get("event") != "market_event":
                continue
            ts = ev.get("exchange_ts_ns")
            if ts is not None:
                ts_epoch = float(ts) / 1e9
            else:
                ts_epoch = float(ev.get("local_ts_epoch", 0.0))
            if start <= ts_epoch < cutoff:
                out.append(ev)
        return out
