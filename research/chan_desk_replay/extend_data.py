#!/usr/bin/env python3
"""Extend BTCUSDT-PERP 1m + 1m_of + aggTrades back to TAPE_START (90d)."""
from __future__ import annotations

import io
import json
import subprocess
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from chan_desk_replay.paths import AGG_DAILY, DATA, KLINE_1M, OF_1M, TAPE_END, TAPE_START

KLINE_BASE = "https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1m"
TRADE_BASE = "https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT"
ZIP_K = DATA / "klines_zip"
ZIP_T = DATA / "aggTrades" / "zip"


def _days(start: date, end: date) -> list[date]:
    out = []
    d = start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def _curl(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        try:
            with zipfile.ZipFile(dest) as zf:
                if zf.namelist():
                    return
        except zipfile.BadZipFile:
            dest.unlink()
    print(f"GET {dest.name}", flush=True)
    subprocess.check_call(
        ["curl", "-fsSL", "--retry", "8", "--retry-all-errors", "--retry-delay", "2", "-o", str(dest), url]
    )


def _read_kline_zip(zpath: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zpath) as zf:
        raw = zf.read(zf.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), header=None)
    if str(df.iloc[0, 0]).lower().startswith("open"):
        df = df.iloc[1:].reset_index(drop=True)
    df = df.iloc[:, :11]
    df.columns = [
        "open_time_ms",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time_ms",
        "quote_volume",
        "n_trades",
        "taker_buy_base",
        "taker_buy_quote",
    ]
    df["open_time_ms"] = pd.to_numeric(df["open_time_ms"], errors="coerce")
    df["open_ts"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "volume", "taker_buy_base"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["n_trades"] = pd.to_numeric(df["n_trades"], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close", "volume"])


def _read_trade_zip(zpath: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zpath) as zf:
        raw = zf.read(zf.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw))
    cols = {c.lower().strip(): c for c in df.columns}
    price = cols.get("price")
    qty = cols.get("quantity") or cols.get("qty")
    ts_col = cols.get("transact_time") or cols.get("time") or cols.get("t")
    maker = cols.get("is_buyer_maker")
    if not all([price, qty, ts_col, maker]):
        df = pd.read_csv(
            io.BytesIO(raw),
            header=None,
            names=["agg_id", "price", "qty", "first_id", "last_id", "T", "is_buyer_maker"],
        )
        price, qty, ts_col, maker = "price", "qty", "T", "is_buyer_maker"
    out = pd.DataFrame(
        {
            "ts": pd.to_datetime(df[ts_col], unit="ms", utc=True),
            "price": pd.to_numeric(df[price], errors="coerce"),
            "qty": pd.to_numeric(df[qty], errors="coerce"),
            "is_buyer_maker": df[maker].astype(str).str.lower().isin(["true", "1"]),
        }
    ).dropna()
    return out


def main() -> None:
    t0 = pd.Timestamp(TAPE_START)
    t1 = pd.Timestamp(TAPE_END)
    d0 = t0.date()
    d1 = t1.date()
    days = _days(d0, d1)

    parts = []
    for d in days:
        zpath = ZIP_K / f"BTCUSDT-1m-{d.isoformat()}.zip"
        _curl(f"{KLINE_BASE}/BTCUSDT-1m-{d.isoformat()}.zip", zpath)
        parts.append(_read_kline_zip(zpath))
    k = pd.concat(parts, ignore_index=True)
    k = k[(k["open_ts"] >= t0) & (k["open_ts"] <= t1)].drop_duplicates("open_ts").sort_values("open_ts")
    of = k[
        ["open_time_ms", "open", "high", "low", "close", "volume", "n_trades", "taker_buy_base", "open_ts"]
    ].copy()
    ohlcv = k[["open_time_ms", "open", "high", "low", "close", "volume", "open_ts"]].copy()
    ohlcv["open"] = ohlcv["open"].map(lambda x: f"{float(x):.2f}")
    ohlcv["high"] = ohlcv["high"].map(lambda x: f"{float(x):.2f}")
    ohlcv["low"] = ohlcv["low"].map(lambda x: f"{float(x):.2f}")
    ohlcv["close"] = ohlcv["close"].map(lambda x: f"{float(x):.2f}")
    ohlcv["volume"] = ohlcv["volume"].map(lambda x: str(x))
    DATA.mkdir(parents=True, exist_ok=True)
    ohlcv.to_parquet(KLINE_1M, index=False)
    of.to_parquet(OF_1M, index=False)
    man = {
        "symbol": "BTCUSDT-PERP",
        "interval": "1m",
        "start": str(t0),
        "end": str(t1),
        "rows": int(len(ohlcv)),
        "first_open": str(ohlcv["open_ts"].iloc[0]),
        "last_open": str(ohlcv["open_ts"].iloc[-1]),
    }
    (DATA / "1m.manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    of_man = dict(man)
    of_man["fields"] = "ohlcv + n_trades + taker_buy_base"
    of_man["path"] = str(OF_1M)
    (DATA / "1m_of.manifest.json").write_text(json.dumps(of_man, indent=2) + "\n")
    print(f"1m rows={len(ohlcv)} {ohlcv['open_ts'].iloc[0]} → {ohlcv['open_ts'].iloc[-1]}", flush=True)

    AGG_DAILY.mkdir(parents=True, exist_ok=True)
    for d in days:
        dest = AGG_DAILY / f"{d.isoformat()}.parquet"
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        zpath = ZIP_T / f"{d.isoformat()}.zip"
        _curl(f"{TRADE_BASE}/BTCUSDT-aggTrades-{d.isoformat()}.zip", zpath)
        _read_trade_zip(zpath).to_parquet(dest, index=False)
        print(f"agg {d} n={dest.stat().st_size}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
