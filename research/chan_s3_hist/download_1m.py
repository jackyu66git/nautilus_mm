"""Download BTCUSDT 1m monthly zips from data.binance.vision. Not the 90d tape."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
sys.path.insert(0, str(ROOT / "research"))

from chan_s3_hist.paths import CENSUS_END, DATA, DATA_START, KLINE_1M, ZIP_K

MONTHLY = "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m"
DAILY = "https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1m"


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


def _read_zip(zpath: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zpath) as zf:
        raw = zf.read(zf.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), header=None)
    if str(df.iloc[0, 0]).lower().startswith("open"):
        df = df.iloc[1:].reset_index(drop=True)
    df = df.iloc[:, :6]
    df.columns = ["open_time_ms", "open", "high", "low", "close", "volume"]
    df["open_time_ms"] = pd.to_numeric(df["open_time_ms"], errors="coerce")
    df["open_ts"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close", "volume"])


def _months(d0: date, d1: date) -> list[str]:
    out = []
    y, m = d0.year, d0.month
    while (y, m) <= (d1.year, d1.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def _days(d0: date, d1: date) -> list[date]:
    out = []
    d = d0
    while d <= d1:
        out.append(d)
        d += timedelta(days=1)
    return out


def main() -> None:
    t0 = pd.Timestamp(DATA_START)
    t1 = pd.Timestamp(CENSUS_END)
    d0, d1 = t0.date(), (t1 - pd.Timedelta(minutes=1)).date()
    DATA.mkdir(parents=True, exist_ok=True)
    parts = []
    months = _months(d0.replace(day=1), date(d1.year, d1.month, 1) - timedelta(days=1))
    # Full months except the last calendar month, which may be incomplete vs CENSUS_END.
    last_full = date(d1.year, d1.month, 1)
    for ym in _months(date(d0.year, d0.month, 1), last_full - timedelta(days=1)):
        zpath = ZIP_K / f"BTCUSDT-1m-{ym}.zip"
        _curl(f"{MONTHLY}/BTCUSDT-1m-{ym}.zip", zpath)
        parts.append(_read_zip(zpath))
    for d in _days(last_full, d1):
        zpath = ZIP_K / f"BTCUSDT-1m-{d.isoformat()}.zip"
        _curl(f"{DAILY}/BTCUSDT-1m-{d.isoformat()}.zip", zpath)
        parts.append(_read_zip(zpath))
    k = pd.concat(parts, ignore_index=True)
    k = k[(k["open_ts"] >= t0) & (k["open_ts"] < t1)].drop_duplicates("open_ts").sort_values("open_ts")
    ohlcv = k[["open_time_ms", "open", "high", "low", "close", "volume", "open_ts"]].copy()
    ohlcv.to_parquet(KLINE_1M, index=False)
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
    print(f"1m rows={len(ohlcv)} {man['first_open']} → {man['last_open']}", flush=True)


if __name__ == "__main__":
    main()
