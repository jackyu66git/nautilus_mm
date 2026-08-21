"""Living 1H ZS expansion vs next 15m bi_dir flip. Location cut already closed."""
from __future__ import annotations

from collections import Counter, defaultdict

import pandas as pd

from chan_htf_zs_ltf_rev.scan import flipped, living_current

PROCESS = ("EXPAND", "STABLE", "NEW_BOX", "NONE")


def process_state(prev: dict | None, live: dict | None) -> str:
    if live is None:
        return "NONE"
    if prev is None or prev.get("zs_id") != live["zs_id"]:
        return "NEW_BOX"
    if int(live["n_bis"] or 0) > int(prev.get("n_bis") or 0):
        return "EXPAND"
    return "STABLE"


def scan_expand(tape: list[dict], bar_15m: pd.DataFrame, book) -> list[dict]:
    by_t = {}
    for r in tape:
        ts = pd.Timestamp(r["t"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        by_t[ts] = r
    rows = []
    prev_live = None
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
        state = process_state(prev_live, live)
        rows.append(
            {
                "t": str(close_ts),
                "state": state,
                "n_bis": None if live is None else int(live["n_bis"] or 0),
                "rev": flipped(rec.get("ltf_bi_dir"), nxt.get("ltf_bi_dir")),
                "label_b1": bool(nxt.get("b1_lock")),
            }
        )
        prev_live = live
    return rows


def _table(rows: list[dict], key: str, order: list | None) -> list[dict]:
    buckets = defaultdict(lambda: Counter())
    for r in rows:
        val = r[key]
        if val is None:
            continue
        buckets[val]["n"] += 1
        if r["rev"]:
            buckets[val]["n_rev"] += 1
        if r["label_b1"]:
            buckets[val]["n_b1"] += 1
    if order is None:
        keys = sorted(buckets)
    else:
        keys = list(order)
    out = []
    for k in keys:
        c = buckets.get(k) or Counter()
        n = int(c["n"])
        n_rev = int(c["n_rev"])
        out.append(
            {
                "level": k,
                "n": n,
                "n_rev": n_rev,
                "rev_share": round(n_rev / n, 6) if n else None,
                "label_b1": int(c["n_b1"]),
                "thin": n > 0 and n < 30,
            }
        )
    return out


def contrast_kind(table: list[dict], overall: float) -> str:
    shares = [r["rev_share"] for r in table if r["n"] >= 30 and r["rev_share"] is not None]
    if len(shares) < 2:
        return "SAMPLE_INSUFFICIENT"
    if max(abs(s - overall) for s in shares) < 0.02:
        return "NO_STATE_CONTRAST"
    return "HAS_CONTRAST"


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    n_rev = sum(1 for r in rows if r["rev"])
    overall = n_rev / n if n else 0.0
    proc = _table(rows, "state", list(PROCESS))
    nbis = _table([r for r in rows if r["n_bis"] is not None], "n_bis", None)
    return {
        "n_bar": n,
        "n_rev": n_rev,
        "rev_share": round(overall, 6),
        "process": proc,
        "n_bis": nbis,
        "process_kind": contrast_kind(proc, overall),
        "n_bis_kind": contrast_kind(nbis, overall),
    }
