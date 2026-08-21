# Research Freeze / Data Collection Phase

**研究框架已冻结。** 研究对象：可验证的市场现象（不是策略）。

验证的假设是：

> 在当前 BTC 永续、当前交易所、当前报价假设、当前执行条件下，被动成交是否产生正向 Maker Alpha。

不是：「我的策略有没有赚钱」。

| 报告结论 | 含义 | 下一步 |
|----------|------|--------|
| **FAIL** | 这个市场假设不成立 | 换假设（Carry / Basis / Funding…） |
| **PARTIAL_PASS** | 优势仅局部存在 | Event-driven LP |
| **PASS** | 普遍可捕获 | Economic Simulation → Symmetric MM |
| **COLLECTING** | 样本不足 | 继续采集 |

三个答案都推进系统。只有盈利才算成功 —— 错误。

---

## 状态机（锁定）

```
Research Freeze
        |
        v
Data Collection
        |
        v
Maker Edge Report v0.1
        |
        +---- FAIL --------------→ 换假设
        |
        +---- PARTIAL_PASS ------→ Event-driven LP
        |
        +---- PASS --------------→ Economic Simulation
        |                              ↓
        |                         Symmetric MM / Quote Engine
        |
        +---- COLLECTING --------→ 继续采集
```

---

## 观察窗口（不要过早解释）

| 规模 | 用途 |
|------|------|
| **~500 fills** | 发现异常 / 管道是否工作 |
| **~2000 fills** | 初步判断（Decision 门槛默认） |
| **~10000 fills** | 才讨论稳定性 |

**cluster 数量比 fill 数量更重要。**  
5000 fills / 80 clusters ≠ 3000 fills / 900 clusters。

第一份报告最值得看的不是 Decision，而是三个**分布**：Fill Alpha / Cluster Alpha / Toxicity。

---

## Unlock Stage3（Economic Simulation）必须同时满足

```
Data Integrity PASS
AND cluster-weighted MakerAlpha > 0
AND benchmark-adjusted alpha > 0
AND edge not concentrated in one event/regime
```

否则：继续 Data Collection，或判定 FAIL / PARTIAL_PASS。  
**禁止**用改 Quote Logic / 改成本假设 来「凑」解锁。

---

## 冻结期间只允许 / 禁止

### ✅ 允许

- 数据字段（不改变报价行为）
- 数据质量检查
- 报告解释能力（分布、归因、可比格式）

### ❌ 禁止（直到 Gate 解锁）

- 新交易规则 / 动态 spread / inventory skew
- 新过滤条件（Pulse / AI）
- 新收益优化参数（为结果改 fee/slip/latency）

### 三不动

1. Quote Logic  
2. 成本模型：`Net = Raw − Fee − Slip − Latency`  
3. 失败定义：`PASS` / `PARTIAL_PASS` / `COLLECTING` / `FAIL`

---

## Report v0.1 固定格式

```
Executive Summary
Section 1 — Data Integrity
Section 2 — Fill Alpha          (+ distribution: mean/median/p25/p75)
Section 3 — Toxicity Profile    (+ loss concentration)
Section 4 — Observed Edge Attribution   (事实，非策略建议)
Section 5 — Decision            + Stage3 unlock checklist
```

第一份报告不期待 PASS。价值在于：市场在哪些情况下愿意付给流动性提供者溢价。

---

## Experiment ID（强制绑定）

每轮 Data Collection 绑定固定身份，写入每条 jsonl + 每份报告：

```
Experiment: MM_EDGE_EXP_001
Version:    probe_v0.1
Quote:      frozen
Fee:        frozen
Exchange:   frozen
```

环境变量：`EXPERIMENT_ID` / `PROBE_VERSION`（见 `.env.example`）。  
换实验假设时换新 ID（如 `MM_EDGE_EXP_002`），禁止在同一 ID 下改报价逻辑后重解释旧数据。

报告阅读顺序：**Integrity → 分布（非均值）→ Cluster → Toxicity → Decision**。  
Integrity FAIL → `Decision=INVALID`，不解释 Alpha。

---

## Post-Report Phase (2026-08-18)

Maker Edge Report → **PARTIAL_PASS**.  
Account wallet moved ≈ −62 USDT vs assumed 5000 start — **not** Maker Edge FAIL evidence;  
also **not** ignorable. Research markout ≠ account equity.

**Probe volume STOPPED** until:

1. Maker-only hard check: `TAKER_FILLED_COUNT == 0` (exchange `userTrades.maker`)
2. Order→Fill→Fee→Position→Funding→Equity ledger residual ≈ 0

See `STATUS.md` and `scripts/reconcile_account.py`.

Stage3 remains **LOCKED**. Economic Edge = **UNKNOWN**.

---

## Economic Attribution Phase (2026-08-18)

`MM_EDGE_EXP_001 / probe_v0.1` is now a **FROZEN BASELINE**.

Execution state:

- Probe: **STOPPED**
- Strategy modifications: **forbidden**
- Purpose: **Economic Attribution only**

First hard-evidence population:

```
MATCHED = 3890
```

This means:

- Local Fill
- Venue Trade
- venue_trade_id
- quantity closure
- price verification
- fee verification
- maker-only verification

Economic Attribution v0.1 must:

1. Use **MATCHED only** for core conclusions
2. Keep `VENUE_CONFIRMED_NO_TRADE_HISTORY` / `VENUE_PARTIAL_ORDER_CANCELED`
   as extension evidence, not core population
3. Treat counterfactuals as **attribution**, not backtest / simulation

Current baseline conclusion:

> Maker markout exists, but economic edge is **not established** under v0.1.

Known explanation path:

```
MakerAlpha
   ↓
matched fills
   ↓
fee + realized / inventory economics
   ↓
account outcome
```

Next allowed work:

- Fee attribution
- Inventory carry / exposure attribution
- Counterfactual attribution (`Path C`, toxic, negative states)
- Real-time immutable fill ledger design for future runs

Still forbidden:

- Resume v0.1 live execution
- Change quote offset / TTL / cooldown as a shortcut
- Unlock Stage3 from attribution alone

---

## Prefill Adverse-Selection Attribution Phase (2026-08-18)

Purpose: **Pre-fill adverse-selection predictability audit** — NOT strategy / backtest / optimization / model training.

Hard contract:

```
feature_timestamp <= t_fill - 0.25s
```

Features: sampled `mid_tick` / `inventory_tick` only.  
Forbidden as features: fill price, post-fill states, Path A/B/C/D, markout, future book/trade/inventory, realized PnL, cancel-after-fill.

Population: **MATCHED paths = 3886** (100% strict coverage)

Executability gate (three tiers):

| Grade | Meaning |
|-------|---------|
| `NO_PREFILL_SIGNAL` | P(C) / economic almost unchanged |
| `STATISTICAL_SIGNAL_ONLY` | probability shift, economic improvement insufficient |
| `CANDIDATE_V0_2_SIGNAL` | probability + economic separation — only this enters v0.2 hypothesis |

Sample-size policy:

- n < 30 → `LOW_N` (exploratory only)
- n < 100 → `WEAK_EVIDENCE`
- n >= 100 → `USABLE`

v0.1 strict conclusion:

> **0 / 19 features** reach `CANDIDATE_V0_2_SIGNAL`.  
> Fill 前可观测信号不足以支撑 v0.2 设计。Stage 3 remains **LOCKED**.

Deferred (requires richer pre-fill event log):

- `time_since_last_market_event`
- intensity / large trades
- fill-callback `market_event_before_fill`

Still forbidden:

- Treat `STATISTICAL_SIGNAL_ONLY` as v0.2 candidate
- Resume probe or design v0.2 strategy without new experiment ID + prefill signal pass

---

## MM_EDGE_EXP_002 — Event-State Observability (2026-08-18)

**Type:** Data Collection / Observability Experiment  
**NOT:** strategy experiment, backtest, optimization, model training

```
MM_EDGE_EXP_001  →  phenomenon PASS, economic FAIL, prefill FAIL (snapshot)
MM_EDGE_EXP_002  →  close observability gap (immutable event ledger)
                 →  Gate 4 only after Gates 1–3 + fill anchors
                 →  (only then) v0.2 hypothesis allowed
```

Identity:

| Field | Value |
|-------|-------|
| Experiment | MM_EDGE_EXP_002 |
| Probe | event_state_v0.1 |
| Strategy | NONE |
| Trading | NO |
| Stage 3 | LOCKED |
| Depends on | MM_EDGE_EXP_001 FROZEN |

Core change: **Immutable Event Ledger** — raw events first, features offline later.

Pre-fill window schema (frozen):

```
[-5s, fill - 250ms)  →  all market_event rows
fill_anchor          →  immutable fill metadata (Gate 4; Phase 1 may have none)
```

Success gates:

1. **Event Completeness** — PASS (smoke)
2. **Temporal Integrity** — PASS (smoke)
3. **Event Coverage** — PASS (smoke)
4. **Predictability** — BLOCKED until frozen sample gates in `MM_EDGE_EXP_002.md`

Long-run: `EXP-002-RUN-002` / `event-state-probe.service` / trading=NO.

Frozen before long-run (do not change after seeing more data):

- Phase 1 dataset: ≥ 7 days AND ≥ 5,000,000 market events
- Gate 4: ≥ 2,000 MATCHED fill_anchors AND ≥ 500 clusters (requires later fill-authorized phase)

No daily Path C analysis during collection.

Still forbidden:

- Resume EXP_001 or modify v0.1 quote logic
- Enable trading under EXP_002
- Unlock Stage 3 from observability data alone
- Peek at Gate 4 before the frozen sample threshold
