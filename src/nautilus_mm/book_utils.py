"""Order book → MicroSnapshot helpers (Nautilus OrderBook / dict)."""

from __future__ import annotations

from typing import Any, Optional

from nautilus_mm.recorder import MicroSnapshot


def snapshot_from_nautilus_book(
    book,
    levels: int = 10,
    recent_buy_qty: float = 0.0,
    recent_sell_qty: float = 0.0,
    last_mid: float | None = None,
    liq_low: float | None = None,
    liq_high: float | None = None,
) -> MicroSnapshot:
    """Convert nautilus_trader OrderBook to MicroSnapshot."""
    try:
        bids = list(book.bids())[:levels] if callable(getattr(book, "bids", None)) else []
        asks = list(book.asks())[:levels] if callable(getattr(book, "asks", None)) else []
    except Exception:
        # Some versions expose bid/ask sequences differently
        bids = getattr(book, "bids", [])[:levels] or []
        asks = getattr(book, "asks", [])[:levels] or []

    def _px_qty(level) -> tuple[float, float]:
        # Nautilus BookLevel: price is attribute, size() is method
        if hasattr(level, "price") and hasattr(level, "size"):
            size = level.size() if callable(level.size) else level.size
            return float(level.price), float(size)
        if isinstance(level, (list, tuple)) and len(level) >= 2:
            return float(level[0]), float(level[1])
        return 0.0, 0.0

    if not bids or not asks:
        # try best bid/ask API
        try:
            bb = float(book.best_bid_price()) if book.best_bid_price() is not None else 0.0
            ba = float(book.best_ask_price()) if book.best_ask_price() is not None else 0.0
            bs = float(book.best_bid_size() or 0)
            az = float(book.best_ask_size() or 0)
            if bb and ba:
                mid = (bb + ba) / 2
                return MicroSnapshot(
                    best_bid=bb,
                    best_ask=ba,
                    mid=mid,
                    spread=ba - bb,
                    bid_depth_1=bs,
                    ask_depth_1=az,
                    bid_depth_5=bs,
                    ask_depth_5=az,
                    bid_depth=bs,
                    ask_depth=az,
                    obi=((bs - az) / (bs + az)) if (bs + az) else 0.0,
                )
        except Exception:
            return MicroSnapshot()
        return MicroSnapshot()

    bid_levels = [_px_qty(x) for x in bids]
    ask_levels = [_px_qty(x) for x in asks]
    best_bid, bid1 = bid_levels[0]
    best_ask, ask1 = ask_levels[0]
    mid = (best_bid + best_ask) / 2.0
    spread = best_ask - best_bid

    def depth(lvls, n):
        return sum(q for _, q in lvls[:n])

    bid_depth_5 = depth(bid_levels, 5)
    ask_depth_5 = depth(ask_levels, 5)
    bid_depth = depth(bid_levels, levels)
    ask_depth = depth(ask_levels, levels)
    tot = bid_depth + ask_depth
    obi = ((bid_depth - ask_depth) / tot) if tot else 0.0

    delta = recent_buy_qty - recent_sell_qty
    timb_den = recent_buy_qty + recent_sell_qty
    trade_imbalance = (delta / timb_den) if timb_den else 0.0

    de = 0.0
    if last_mid and mid and abs(delta) > 1e-12:
        de = ((mid - last_mid) / last_mid) / delta

    liq_dist = 0.0
    if liq_low and liq_high and mid and (liq_high - liq_low) > 0:
        liq_dist = ((mid - liq_low) / (liq_high - liq_low)) * 2 - 1

    return MicroSnapshot(
        best_bid=best_bid,
        best_ask=best_ask,
        mid=mid,
        spread=spread,
        bid_depth_1=bid1,
        ask_depth_1=ask1,
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


def snapshot_from_ccxt_ob(
    ob: dict[str, Any],
    levels: int = 10,
    recent_trades: list | None = None,
    last_mid: float | None = None,
) -> MicroSnapshot:
    from nautilus_mm.recorder import MakerEdgeLogger

    return MakerEdgeLogger.snapshot_from_orderbook(
        ob,
        levels=levels,
        recent_trades=recent_trades,
        last_mid=last_mid,
    )
