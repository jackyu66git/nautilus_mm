"""15m KLC check_fx clock. Geometry only. No bi / zs / bsp."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from chanlun.core.ChanEnum import Chan_FX_TYPE
from chanlun.core.ChanKLU import ChanKLU
from chanlun.pipeline.timeframe import TF_DF

BAR_MINUTES = 15


def _pad_klu(klu: ChanKLU) -> ChanKLU:
    for name in (
        "ema13",
        "ema7",
        "ema5",
        "ma5",
        "ema_dir",
    ):
        if not hasattr(klu, name):
            setattr(klu, name, 0)
    return klu


def resample_bars(kline_1m: pd.DataFrame, minutes: int) -> pd.DataFrame:
    s = kline_1m.copy()
    s["open_ts"] = pd.to_datetime(s["open_ts"], utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        s[col] = pd.to_numeric(s[col], errors="coerce")
    s = s.dropna(subset=["open", "high", "low", "close", "volume"]).set_index("open_ts").sort_index()
    bar = s.resample(f"{minutes}min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    bar = bar.dropna()
    bar["open_ts"] = bar.index
    bar["close_ts"] = bar["open_ts"] + pd.Timedelta(minutes=minutes)
    return bar.reset_index(drop=True)


def resample_15m(kline_1m: pd.DataFrame) -> pd.DataFrame:
    return resample_bars(kline_1m, BAR_MINUTES)


def _parse_engine_time(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz="UTC")


@dataclass
class FractalEvent:
    fx_id: str
    fx_side: str
    mid_start: pd.Timestamp
    T_FX_VISIBLE: pd.Timestamp
    forming_ts: pd.Timestamp | None = None
    candidate_ts: pd.Timestamp | None = None
    confirmed_ts: pd.Timestamp | None = None
    retracted: bool = False
    left_start: pd.Timestamp | None = None
    left_end: pd.Timestamp | None = None
    mid_end: pd.Timestamp | None = None
    right_start: pd.Timestamp | None = None
    right_end: pd.Timestamp | None = None
    mid_high: float = 0.0
    mid_low: float = 0.0
    mid_range: float = 0.0


@dataclass
class ClockState:
    events: list[FractalEvent] = field(default_factory=list)
    n_15m: int = 0
    n_klc: int = 0


def _klc_span(klc, bar_minutes: int = BAR_MINUTES) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = _parse_engine_time(klc.start_klu.time)
    last = klc.end_klu or klc.klu_list[-1]
    end = _parse_engine_time(last.time) + pd.Timedelta(minutes=bar_minutes)
    return start, end


def replay_fractal_clock(bar_15m: pd.DataFrame, bar_minutes: int = BAR_MINUTES) -> ClockState:
    engine = TF_DF()
    klc_list: list = []
    last_klu = None
    visible: dict[str, FractalEvent] = {}
    forming_at: dict[int, pd.Timestamp] = {}
    candidate_at: dict[int, pd.Timestamp] = {}
    state = ClockState()

    for i, row in bar_15m.iterrows():
        state.n_15m += 1
        close_ts = pd.Timestamp(row["close_ts"])
        if close_ts.tzinfo is None:
            close_ts = close_ts.tz_localize("UTC")
        time_str = pd.Timestamp(row["open_ts"]).tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S")
        klu = _pad_klu(
            ChanKLU(
                time_str,
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            )
        )
        klu.set_idx(int(i))
        if last_klu is not None:
            last_klu.set_next(klu)
            klu.set_pre(last_klu)
        n_before = len(klc_list)
        engine._push_klu_into_klc_list(klc_list, klu, last_klu)
        last_klu = klu
        if len(klc_list) > n_before and n_before > 0:
            prev = klc_list[-2]
            if prev.end_klu is not None:
                forming_at.setdefault(id(prev), close_ts)
        if len(klc_list) >= 2:
            maybe_mid = klc_list[-2]
            if maybe_mid.next is klc_list[-1] and klc_list[-1].end_klu is None:
                candidate_at.setdefault(id(maybe_mid), close_ts)

        for klc in klc_list:
            if klc.pre is None or klc.next is None or klc.next.end_klu is None:
                continue
            fx = engine.check_fx(klc)
            if fx not in (Chan_FX_TYPE.BOTTOM, Chan_FX_TYPE.TOP):
                fx_id = klc.start_time
                if fx_id in visible and not visible[fx_id].retracted:
                    visible[fx_id].retracted = True
                continue
            fx_id = klc.start_time
            side = "BOTTOM" if fx == Chan_FX_TYPE.BOTTOM else "TOP"
            if fx_id not in visible:
                left_s, left_e = _klc_span(klc.pre, bar_minutes)
                mid_s, mid_e = _klc_span(klc, bar_minutes)
                right_s, right_e = _klc_span(klc.next, bar_minutes)
                visible[fx_id] = FractalEvent(
                    fx_id=fx_id,
                    fx_side=side,
                    mid_start=mid_s,
                    T_FX_VISIBLE=close_ts,
                    forming_ts=forming_at.get(id(klc)),
                    candidate_ts=candidate_at.get(id(klc)),
                    left_start=left_s,
                    left_end=left_e,
                    mid_end=mid_e,
                    right_start=right_s,
                    right_end=right_e,
                    mid_high=float(klc.high),
                    mid_low=float(klc.low),
                    mid_range=float(klc.high) - float(klc.low),
                )
            elif not visible[fx_id].retracted:
                visible[fx_id].confirmed_ts = close_ts

    state.n_klc = len(klc_list)
    state.events = list(visible.values())
    return state
