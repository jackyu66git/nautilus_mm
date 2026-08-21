#!/usr/bin/env python3
"""
Validate MM_EDGE_EXP_002 Immutable Event Ledger.

Phase 1 smoke: Gates 1–3 plus ledger engineering contract.
Gate 4 (predictability) is blocked until fill anchors exist.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any


TRADE_REQUIRED = [
    "event_type",
    "exchange_ts_ns",
    "local_ts_epoch",
    "local_ts_ns",
    "trade_side",
    "trade_qty",
    "trade_price",
    "best_bid",  # optional on trade; counted separately
]
TRADE_CORE = [
    "event_type",
    "exchange_ts_ns",
    "local_ts_epoch",
    "local_ts_ns",
    "trade_side",
    "trade_qty",
    "trade_price",
    "price",
    "quantity",
    "best_bid",
    "best_ask",
    "mid",
    "spread",
]
BOOK_CORE = [
    "event_type",
    "exchange_ts_ns",
    "local_ts_epoch",
    "local_ts_ns",
    "best_bid",
    "best_ask",
    "mid",
    "spread",
    "bid_depth_1",
    "ask_depth_1",
    "bid_depth_5",
    "ask_depth_5",
]
BOOK_DELTA_KEYS = [
    "bid_depth_delta_1",
    "ask_depth_delta_1",
    "bid_move",
    "ask_move",
    "spread_change",
]


def _pctile(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    i = (len(ys) - 1) * q
    lo = math.floor(i)
    hi = math.ceil(i)
    if lo == hi:
        return ys[lo]
    return ys[lo] * (hi - i) + ys[hi] * (i - lo)


def _num(v: float | None, digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v:.{digits}f}"


def load_jsonl(log_dir: Path) -> tuple[list[dict[str, Any]], int, int]:
    rows: list[dict[str, Any]] = []
    parse_fail = 0
    empty = 0
    for f in sorted(log_dir.glob("*.jsonl")):
        for line in f.open():
            s = line.strip()
            if not s:
                empty += 1
                continue
            try:
                e = json.loads(s)
            except Exception:
                parse_fail += 1
                continue
            if isinstance(e, dict):
                rows.append(e)
            else:
                parse_fail += 1
    return rows, parse_fail, empty


def _present(ev: dict[str, Any], key: str) -> bool:
    v = ev.get(key)
    return v is not None and v != ""


def _hollow_book(ev: dict[str, Any]) -> bool:
    depths = [
        ev.get("bid_depth_1"),
        ev.get("ask_depth_1"),
        ev.get("bid_depth_5"),
        ev.get("ask_depth_5"),
        ev.get("mid"),
    ]
    nums = []
    for d in depths:
        try:
            nums.append(float(d))
        except (TypeError, ValueError):
            nums.append(0.0)
    return all(abs(x) < 1e-12 for x in nums)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate EXP_002 event ledger / smoke contract")
    ap.add_argument("--dir", default="logs/event_state")
    ap.add_argument("--out", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--sample", type=int, default=200)
    ap.add_argument("--latency-tolerance-ms", type=float, default=50.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    log_dir = Path(args.dir)
    rows, parse_fail, empty_lines = load_jsonl(log_dir)
    if args.run_id:
        rows = [r for r in rows if r.get("run_id") == args.run_id]

    market = [r for r in rows if r.get("event") == "market_event"]
    trades = [r for r in market if r.get("event_type") == "aggressive_trade"]
    books = [r for r in market if r.get("event_type") == "book_update"]
    starts = [r for r in rows if r.get("event") == "experiment_start"]
    stops = [r for r in rows if r.get("event") == "experiment_stop"]
    anchors = [r for r in rows if r.get("event") == "fill_anchor"]

    run_ids = sorted({r.get("run_id") for r in rows if r.get("run_id")})
    sessions = [r.get("session_id") for r in starts]

    # Duration from first/last local_ts
    local_epochs = [float(r["local_ts_epoch"]) for r in market if r.get("local_ts_epoch") is not None]
    duration_s = (max(local_epochs) - min(local_epochs)) if len(local_epochs) >= 2 else 0.0
    if duration_s <= 0:
        duration_s = 1.0

    rates = {
        "aggressive_trade_per_sec": len(trades) / duration_s,
        "book_update_per_sec": len(books) / duration_s,
        "total_market_events_per_sec": len(market) / duration_s,
        "duration_sec": duration_s,
    }

    # Timestamp quality
    ex_ok = sum(1 for r in market if r.get("exchange_ts_ns") is not None)
    loc_ok = sum(1 for r in market if r.get("local_ts_epoch") is not None and r.get("local_ts_ns") is not None)
    latencies_ms: list[float] = []
    skew_violations = 0
    for r in market:
        ex = r.get("exchange_ts_ns")
        loc = r.get("local_ts_ns")
        if ex is None or loc is None:
            continue
        lag_ms = (float(loc) - float(ex)) / 1e6
        latencies_ms.append(lag_ms)
        if float(ex) > float(loc) + args.latency_tolerance_ms * 1e6:
            skew_violations += 1

    ts_quality = {
        "exchange_ts_ns_pct": (ex_ok / len(market)) if market else 0.0,
        "local_ts_pct": (loc_ok / len(market)) if market else 0.0,
        "latency_n": len(latencies_ms),
        "latency_ms_p50": _pctile(latencies_ms, 0.50),
        "latency_ms_p95": _pctile(latencies_ms, 0.95),
        "latency_ms_p99": _pctile(latencies_ms, 0.99),
        "latency_ms_max": max(latencies_ms) if latencies_ms else None,
        "latency_ms_min": min(latencies_ms) if latencies_ms else None,
        "exchange_after_local_violations": skew_violations,
        "tolerance_ms": args.latency_tolerance_ms,
    }

    # Event order: exchange_ts regression (do not silently sort)
    regressions = 0
    max_back_ns = 0
    prev_ex = None
    for r in market:
        ex = r.get("exchange_ts_ns")
        if ex is None:
            continue
        ex = int(ex)
        if prev_ex is not None and ex < prev_ex:
            regressions += 1
            max_back_ns = max(max_back_ns, prev_ex - ex)
        prev_ex = ex

    # Schema completeness (sample)
    rng = random.Random(args.seed)
    n_trade_s = min(args.sample, len(trades))
    n_book_s = min(args.sample, len(books))
    trade_sample = rng.sample(trades, n_trade_s) if n_trade_s else []
    book_sample = rng.sample(books, n_book_s) if n_book_s else []

    def missing_rate(sample: list[dict], keys: list[str]) -> dict[str, float]:
        if not sample:
            return {k: 1.0 for k in keys}
        out = {}
        for k in keys:
            miss = sum(1 for e in sample if not _present(e, k))
            out[k] = miss / len(sample)
        return out

    trade_missing = missing_rate(trade_sample, TRADE_CORE)
    book_missing = missing_rate(book_sample, BOOK_CORE)
    book_delta_key_miss = 0.0
    if book_sample:
        book_delta_key_miss = sum(
            1 for e in book_sample if any(k not in e for k in BOOK_DELTA_KEYS)
        ) / len(book_sample)
    hollow = sum(1 for e in book_sample if _hollow_book(e))

    # Restart / integrity
    event_ids = [r.get("event_id") for r in market if r.get("event_id")]
    dup_ids = [k for k, v in Counter(event_ids).items() if v > 1]

    seq_ok = True
    seq_notes = []
    by_session: dict[str, list[int]] = {}
    for r in rows:
        sid = r.get("session_id")
        seq = r.get("event_seq")
        if sid is None or seq is None:
            continue
        by_session.setdefault(str(sid), []).append(int(seq))
    for sid, seqs in by_session.items():
        if seqs != list(range(1, len(seqs) + 1)) and seqs != sorted(seqs):
            # allow gaps only if we filtered; within session expect 1..n
            expected = list(range(min(seqs), max(seqs) + 1))
            if seqs != expected:
                seq_ok = False
                seq_notes.append(f"{sid}: not contiguous {seqs[:5]}...{seqs[-3:]}")
        if seqs and seqs[0] != 1:
            seq_notes.append(f"{sid}: seq starts at {seqs[0]} (expected 1 after restart)")

    seq_reset_expected = len(sessions) >= 2 and all(
        (by_session.get(str(s), [None])[0] == 1) for s in sessions if s
    )

    # Gates
    gate1_pass: bool | None
    if anchors:
        reconstruct_fail = 0
        for anc in anchors:
            fill_ts = float(anc["fill_ts_epoch"])
            start = float(anc.get("window_start_epoch", fill_ts - 5.0))
            cutoff = float(anc.get("feature_cutoff_epoch", fill_ts - 0.25))
            window = []
            for r in market:
                ex = r.get("exchange_ts_ns")
                ts = float(ex) / 1e9 if ex is not None else r.get("local_ts_epoch")
                if ts is None:
                    continue
                if start <= float(ts) < cutoff:
                    window.append(r)
            if not window:
                reconstruct_fail += 1
        gate1_pass = reconstruct_fail == 0
        gate1_status = "PASS" if gate1_pass else "FAIL"
    else:
        # Phase 1: stream completeness stands in for fill reconstruction
        stream_ok = parse_fail == 0 and len(market) > 0 and loc_ok == len(market)
        gate1_pass = stream_ok
        gate1_status = (
            "PASS (Phase 1 stream completeness; no fill_anchor — expected)"
            if stream_ok
            else "FAIL (stream incomplete)"
        )

    gate2_ok = (
        ts_quality["exchange_ts_ns_pct"] >= 0.99
        and ts_quality["local_ts_pct"] >= 0.99
        and skew_violations == 0
    )
    gate2_status = "PASS" if gate2_ok else "FAIL"

    schema_ok = (
        all(v == 0.0 for v in trade_missing.values())
        and all(v == 0.0 for v in book_missing.values())
        and book_delta_key_miss == 0.0
        and hollow == 0
        and len(trades) > 0
        and len(books) > 0
    )
    gate3_ok = schema_ok and ts_quality["exchange_ts_ns_pct"] >= 0.99
    gate3_status = "PASS" if gate3_ok else "FAIL"

    restart_ok = (
        parse_fail == 0
        and len(dup_ids) == 0
        and len(starts) >= 1
        and (len(starts) == 1 or (len(stops) >= len(starts) - 1 and seq_reset_expected))
    )

    integrity = {
        "parse_fail_lines": parse_fail,
        "empty_lines": empty_lines,
        "duplicate_event_ids": len(dup_ids),
        "experiment_start_count": len(starts),
        "experiment_stop_count": len(stops),
        "sessions": sessions,
        "seq_contiguous_ok": seq_ok,
        "seq_reset_expected": seq_reset_expected,
        "seq_notes": seq_notes[:8],
        "restart_contract": "PASS" if restart_ok else "FAIL",
    }

    run_id = args.run_id or (run_ids[0] if len(run_ids) == 1 else ",".join(run_ids) or "UNSET")
    start0 = starts[0] if starts else {}
    manifest = {
        "run_id": run_id,
        "start_ts": start0.get("local_ts"),
        "end_ts": stops[-1].get("local_ts") if stops else (rows[-1].get("local_ts") if rows else None),
        "host": start0.get("host"),
        "commit": start0.get("commit"),
        "config_hash": start0.get("config_hash"),
        "schema_version": start0.get("schema_version"),
        "event_count": len(rows),
        "trade_event_count": len(trades),
        "book_event_count": len(books),
        "session_count": len(sessions),
    }

    report = {
        "experiment_id": start0.get("experiment_id", "MM_EDGE_EXP_002"),
        "run_id": run_id,
        "purpose": "ledger smoke / Gates 1-3",
        "gate4_predictability": "BLOCKED",
        "gates": {
            "gate1_event_completeness": gate1_status,
            "gate2_temporal_integrity": gate2_status,
            "gate3_event_coverage": gate3_status,
        },
        "manifest": manifest,
        "rates": rates,
        "timestamp_quality": ts_quality,
        "order": {
            "exchange_ts_regressions": regressions,
            "max_regression_ns": max_back_ns,
            "max_regression_ms": max_back_ns / 1e6 if regressions else 0.0,
            "note": "regressions recorded, not silently sorted",
        },
        "schema": {
            "trade_sample_n": n_trade_s,
            "book_sample_n": n_book_s,
            "trade_missing_rate": trade_missing,
            "book_missing_rate": book_missing,
            "hollow_book_in_sample": hollow,
        },
        "integrity": integrity,
        "counts": {
            "total_rows": len(rows),
            "market_events": len(market),
            "aggressive_trades": len(trades),
            "book_updates": len(books),
            "fill_anchors": len(anchors),
        },
    }

    lines = [
        "=" * 68,
        "MM_EDGE_EXP_002 Ledger Smoke / Gates 1–3",
        "=" * 68,
        f"run_id:     {run_id}",
        f"sessions:   {len(sessions)} {sessions}",
        f"host/commit:{start0.get('host')} / {str(start0.get('commit') or '')[:12]}",
        f"config_hash:{start0.get('config_hash')}",
        f"schema:     {start0.get('schema_version')}",
        "",
        "Gate 1 Event Completeness:  " + gate1_status,
        "Gate 2 Temporal Integrity:  " + gate2_status,
        "Gate 3 Event Coverage:      " + gate3_status,
        "Gate 4 Predictability:      BLOCKED",
        "",
        "1. Event write rates",
        "-" * 40,
        f"duration_sec:              {_num(duration_s, 1)}",
        f"aggressive_trade / sec:    {_num(rates['aggressive_trade_per_sec'], 3)}",
        f"book_update / sec:         {_num(rates['book_update_per_sec'], 3)}",
        f"total market events / sec: {_num(rates['total_market_events_per_sec'], 3)}",
        f"counts: trades={len(trades)} books={len(books)} total={len(market)}",
        "",
        "2. Timestamp quality",
        "-" * 40,
        f"exchange_ts_ns != null:    {ts_quality['exchange_ts_ns_pct']*100:.2f}%",
        f"local_ts_ns != null:       {ts_quality['local_ts_pct']*100:.2f}%",
        f"exchange > local+tol:      {skew_violations} (tol={args.latency_tolerance_ms}ms)",
        f"local-exchange lag ms:     p50={_num(ts_quality['latency_ms_p50'])} "
        f"p95={_num(ts_quality['latency_ms_p95'])} p99={_num(ts_quality['latency_ms_p99'])} "
        f"max={_num(ts_quality['latency_ms_max'])}",
        "",
        "3. Event order (exchange_ts_ns regression, not sorted)",
        "-" * 40,
        f"regressions: {regressions}  max_back_ms={_num(max_back_ns/1e6 if regressions else 0.0)}",
        "",
        "4. Raw event completeness (sample)",
        "-" * 40,
        f"trade sample={n_trade_s} missing={trade_missing}",
        f"book  sample={n_book_s} missing={book_missing}",
        f"hollow book_update (all depth/mid empty): {hollow}",
        "",
        "5. Restart / immutable integrity",
        "-" * 40,
        f"parse_fail_lines={parse_fail} empty_lines={empty_lines}",
        f"duplicate_event_ids={len(dup_ids)}",
        f"start={len(starts)} stop={len(stops)} seq_ok={seq_ok} seq_reset_expected={seq_reset_expected}",
        f"restart_contract={integrity['restart_contract']}",
        "",
        "Gate 4 remains BLOCKED until fill_anchor exists. Do not resume trading.",
        "=" * 68,
    ]
    text = "\n".join(lines) + "\n"
    print(text)

    out_json = Path(args.out) if args.out else log_dir / "Event_Ledger_Validation.json"
    out_txt = out_json.with_suffix(".txt")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    out_txt.write_text(text, encoding="utf-8")
    (log_dir / f"{run_id.replace('/', '_')}.manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )

    ok = gate1_pass is not False and gate2_ok and gate3_ok and restart_ok and parse_fail == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
