"""Living 1H ZS location vs next 15m bi_dir flip. No OF. B1 is a label."""
from __future__ import annotations

from collections import Counter, defaultdict

import pandas as pd

from chan_htf_hist_anchor.phase0_schema import rail_side
from chan_htf_hist_anchor.replay import HistBook, _htf_at

STATES = ("A_INSIDE", "B_BOUNDARY", "C_AWAY")
DIRS = frozenset({"UP", "DOWN"})


def living_current(book: HistBook, t) -> dict | None:
    t = pd.Timestamp(t)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    zs_map = _htf_at(book, t)
    best = None
    best_birth = None
    for zid, rec in zs_map.items():
        if rec.get("has_next"):
            continue
        born = book.birth.get(zid)
        if born is None:
            continue
        if best_birth is None or born >= best_birth:
            best_birth = born
            best = {"zs_id": zid, "zg": rec["zg"], "zd": rec["zd"], "n_bis": rec.get("n_bis")}
    return best


def zs_loc(low: float, high: float, zg: float, zd: float) -> str:
    if zg is None or zd is None or zg <= zd:
        return "C_AWAY"
    side_zg = rail_side(low, high, zg)
    side_zd = rail_side(low, high, zd)
    if side_zg == "CONTACT" or side_zd == "CONTACT":
        return "B_BOUNDARY"
    if side_zg == "BELOW" and side_zd == "ABOVE":
        return "A_INSIDE"
    return "C_AWAY"


def flipped(a, b) -> bool:
    return a in DIRS and b in DIRS and a != b


def scan(tape: list[dict], bar_15m: pd.DataFrame, book: HistBook) -> list[dict]:
    by_t = {}
    for r in tape:
        ts = pd.Timestamp(r["t"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        by_t[ts] = r
    rows = []
    for i in range(len(bar_15m) - 1):
        close_ts = pd.Timestamp(bar_15m.iloc[i]["close_ts"])
        if close_ts.tzinfo is None:
            close_ts = close_ts.tz_localize("UTC")
        rec = by_t.get(close_ts)
        nxt_ts = pd.Timestamp(bar_15m.iloc[i + 1]["close_ts"])
        if nxt_ts.tzinfo is None:
            nxt_ts = nxt_ts.tz_localize("UTC")
        nxt = by_t.get(nxt_ts)
        if rec is None or nxt is None:
            continue
        live = living_current(book, close_ts)
        if live is None:
            state = "NONE"
            zs_id = None
        else:
            state = zs_loc(
                float(bar_15m.iloc[i]["low"]),
                float(bar_15m.iloc[i]["high"]),
                float(live["zg"]),
                float(live["zd"]),
            )
            zs_id = live["zs_id"]
        rows.append(
            {
                "t": str(close_ts),
                "state": state,
                "zs_id": zs_id,
                "rev": flipped(rec.get("ltf_bi_dir"), nxt.get("ltf_bi_dir")),
                "label_b1": bool(nxt.get("b1_lock")),
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    buckets = defaultdict(lambda: Counter())
    for r in rows:
        buckets[r["state"]]["n"] += 1
        if r["rev"]:
            buckets[r["state"]]["n_rev"] += 1
        if r["label_b1"]:
            buckets[r["state"]]["n_b1"] += 1
    order = list(STATES) + ["NONE"]
    table = []
    for k in order:
        c = buckets.get(k) or Counter()
        n = int(c["n"])
        n_rev = int(c["n_rev"])
        table.append(
            {
                "state": k,
                "n": n,
                "n_rev": n_rev,
                "rev_share": round(n_rev / n, 6) if n else None,
                "label_b1": int(c["n_b1"]),
            }
        )
    n = len(rows)
    n_rev = sum(1 for r in rows if r["rev"])
    return {
        "n_bar": n,
        "n_rev": n_rev,
        "rev_share": round(n_rev / n, 6) if n else None,
        "table": table,
    }
