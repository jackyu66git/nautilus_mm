#!/usr/bin/env python3
"""Download Binance UM daily aggTrades via curl. Same 60d window as 1m kline."""
from __future__ import annotations

import io
import subprocess
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jack/Project/freqtrade/nautilus_mm")
OUT = ROOT / "data" / "chan_2buy_of" / "BTCUSDT-PERP" / "aggTrades"
ZIP_DIR = OUT / "zip"
DAILY = OUT / "daily"
BASE = "https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT"
START = date(2026, 6, 20)
END = date(2026, 8, 19)


def days() -> list[date]:
    d = START
    out = []
    while d <= END:
        out.append(d)
        d += timedelta(days=1)
    return out


def curl_zip(day: date) -> Path:
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    dest = ZIP_DIR / f"{day.isoformat()}.zip"
    url = f"{BASE}/BTCUSDT-aggTrades-{day.isoformat()}.zip"
    cmd = [
        "curl",
        "-fsSL",
        "--retry",
        "8",
        "--retry-all-errors",
        "--retry-delay",
        "2",
        "-o",
        str(dest),
        url,
    ]
    print(f"GET {day}", flush=True)
    subprocess.check_call(cmd)
    return dest


def _zip_ok(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1000:
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            return bool(zf.namelist())
    except zipfile.BadZipFile:
        return False


def zip_to_parquet(day: date) -> Path:
    DAILY.mkdir(parents=True, exist_ok=True)
    dest = DAILY / f"{day.isoformat()}.parquet"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    zpath = ZIP_DIR / f"{day.isoformat()}.zip"
    if not _zip_ok(zpath):
        if zpath.exists():
            zpath.unlink()
        zpath = curl_zip(day)
        if not _zip_ok(zpath):
            raise zipfile.BadZipFile(f"bad zip after retry: {zpath}")
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
    out.to_parquet(dest, index=False)
    print(f"  parquet {day} n={len(out)}", flush=True)
    return dest


def main() -> None:
    ds = days()
    print(f"days={len(ds)} {START}..{END}")
    for d in ds:
        zip_to_parquet(d)
    print("done")


if __name__ == "__main__":
    main()
