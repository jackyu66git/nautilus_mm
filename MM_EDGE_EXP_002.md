# MM_EDGE_EXP_002 — Event-State Observability Probe

## Experiment Identity

```
Experiment:  MM_EDGE_EXP_002
Type:        Data Collection / Observability Experiment
Strategy:    NONE
Execution:   STOPPED (no trading)
Purpose:     Capture immutable pre-fill Event State
Dependency:  MM_EDGE_EXP_001 / v0.1 FROZEN
Stage 3:     LOCKED
```

**NOT:** strategy experiment, backtest, optimization, model training, v0.2 design.

---

## Why EXP_002 Exists

EXP_001 Prefill Audit conclusion:

> Under **current snapshot observability** (~1.66s sampled mid/inventory state), no sufficient pre-fill signal was found.

This must **not** be interpreted as:

> The market has no pre-fill adverse-selection information.

EXP_001 strategy is **event-driven**, but observability was **snapshot-driven**. Information between snapshots (e.g. aggressive sweep 100ms before fill) is lost.

EXP_002 closes the **observability gap**, not the **strategy gap**.

---

## Core Design Principle

```
Raw Event  >  Derived Feature
```

Store immutable events. Features are computed offline later.

---

## Immutable Event Ledger

Each market event records (minimum):

| Field | Description |
|-------|-------------|
| `exchange_ts_ns` | Exchange event time |
| `local_ts_epoch` / `local_ts` | Local receive time |
| `event_type` | `aggressive_trade`, `book_update`, … |
| `best_bid` / `best_ask` / `mid` / `spread` | Top-of-book |
| `bid_depth_*` / `ask_depth_*` | Depth levels |
| `*_delta` | Depth / spread / mid changes |
| `time_since_last_*` | Event timing state |

Fill anchor schema (frozen, for Gate 4 when fills exist):

```
[-5s, fill - 250ms)  →  all market_event rows
fill_anchor            →  immutable fill metadata
```

---

## Event Categories (Priority)

1. **Aggressive Trade** — side, qty, notional, large_trade_flag, intensity proxy
2. **Book Depletion** — depth deltas, level removal velocity
3. **Spread / TOB Event** — spread change, bid/ask/mid move
4. **Event Timing** — time_since_last_trade / large_trade / depth_change / spread_change

---

## Success Gates (frozen before collection)

### Gate 1 — Event Completeness

For each `fill_anchor`:

```
100% reconstructable pre-fill event sequence in [-5s, fill - margin)
```

Phase 1 (observability-only): **N/A** until fill anchors exist.

### Gate 2 — Temporal Integrity

```
all event_ts < fill_ts
feature_cutoff = fill_ts - 250ms
```

### Gate 3 — Event Coverage

| Metric | Threshold |
|--------|-----------|
| trade events present | ≥ 99% of sessions with trades |
| book events present | ≥ 99% of sessions with book updates |
| timestamp valid | ≥ 99% rows with exchange_ts_ns or local_ts |

### Gate 4 — Predictability (BLOCKED until sample freeze + fill anchors)

Do **not** inspect Path C daily during collection (researcher degrees of freedom).

Frozen sample thresholds (**set 2026-08-18, before long-run start**):

**Phase 1 Event-State dataset freeze** (observability-only, no fills):

| Metric | Minimum |
|--------|---------|
| Calendar span | **≥ 7 days** |
| `market_event` count | **≥ 5,000,000** |
| `aggressive_trade` | **≥ 1,500,000** |
| `book_update` | **≥ 3,000,000** |
| timestamp valid | **≥ 99%** |
| parse_fail_lines | **0** |

Reaching this freeze **does not** unlock Gate 4. It only freezes the Event-State stream as a research artifact.

**Gate 4 (requires a later fill-authorized phase, not this systemd job):**

| Metric | Minimum |
|--------|---------|
| MATCHED `fill_anchor` | **≥ 2,000** |
| `event_cluster_id` | **≥ 500** |
| reconstructable `[-5s, fill−250ms)` | **100%** of MATCHED anchors |
| venue_trade_id + exchange_ts_ns on fill | **100%** |

Then, **once**:

```
Event State → P(Path C) → Economic separation
→ CANDIDATE_V0_2_SIGNAL only if both probability and economic gates pass
```

Future fill collection (if ever authorized) **must** write:

```
Fill → venue_trade_id → exchange_ts_ns → Event Ledger → [-5s, fill_ts)
```

Do not resume snapshot-only fills.

Only **CANDIDATE_V0_2_SIGNAL** after Gate 4 may enter v0.2 hypothesis design.

---

## Research Chain

```
EXP_001  Maker Edge Phenomenon
              ↓
         conditional markout exists
              ↓
         Economic FAIL
              ↓
         Prefill audit (snapshot) → NO SIGNAL
              ↓
EXP_002  Event-State Observability
              ↓
         Gate 1–3 PASS?
              ↓
         Gate 4 predictability
              ↓
         (only then) v0.2 hypothesis
```

---

## Running

```bash
cd nautilus_mm
cp .env.example .env   # set EXP_002 block
export PYTHONPATH=src
./scripts/run_event_state.sh
```

Long-run (systemd, trading=NO):

```
LEDGER_RUN_ID=EXP-002-RUN-002
logs/event_state/EXP-002-RUN-002/
```

```bash
systemctl --user start event-state-probe
./scripts/event_state_status.sh   # counts only — not Path C analysis
```

---

## Forbidden

- Resume EXP_001 probe or modify v0.1 quote logic
- Enable trading under EXP_002
- Unlock Stage 3 from observability data alone
- Treat weak EXP_001 statistical signals as v0.2 filters

---

## Hypothesis Closure (if Gate 4 also fails)

> Conditional Maker phenomenon exists, but is not sufficiently predictable pre-fill to be monetizable under this venue/execution model.

That would be a **strong Research FAIL / Hypothesis Closure** — not "try one more parameter."
