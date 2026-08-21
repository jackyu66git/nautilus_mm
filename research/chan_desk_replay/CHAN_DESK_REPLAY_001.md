# CHAN_DESK_REPLAY_001

```
Experiment:     CHAN_DESK_REPLAY_001
Type:           FROZEN FACT BASELINE。不是实验结果。
Status:         DONE / FROZEN
                PASS / STATE_TAPE_OK
Replay:         TAPE-90D 锁定。不准再改钟、窗口、字段语义。
Interpretation: BLOCKED
Trading:        BLOCKED
```

核心边界：

```
t 时刻
  → 机器重建 t 时刻真实可见世界
  → 不解释、不建议、不分类、不交易
```

以后所有实验从本带取当时状态。禁止为了某个假设另起时间窗口。  
时间窗不够、周期不够、样本不够：**开新 ID**，不准回头改本 ID 的钟、窗口或字段语义。

`B1_LOCK` 只表示：截至该时刻，结构引擎已经确认这个状态。不是入场建议。  
90 天里机器确认了 **8** 次，这是稀疏结构事件索引，**不是 8 个交易机会**。

---

## v1 输出边界

| 层 | v1 | 含义 |
|----|----|------|
| 1H HTF leftover | 输出 | 当时已存在的空间记忆。`T_ZS_COMPLETE < t` |
| 15m 笔/分型 | 输出 | 当时已形成的结构。只用已闭合 K |
| B1_LOCK | 输出 | 客观结构旗标 |
| 1m / 成交级 OF | 输出 | 当时窗口原始数值。`open_ts < t` 且 `trade_ts < t`。有分型时另满足 `t_of < T_FX_VISIBLE` |
| SMC | `UNDEFINED` | 尚无 detector。字段名 `smc_state` |
| OF support/against | 禁止 | 主观解释 |
| Allow | 禁止 | 主观交易判断 |
| Entry/Stop/Target | 禁止 | 交易决策 |
| B1→B2 未来标签 | 禁止 | 未来信息 |
| MFE/MAE | 禁止 | 留给下一 ID |

禁止键进 schema，不是留空。见 `schema.py`。

---

## 两条线

**Desk Line — FROZEN FACT BASELINE**。Input = 本带。不准重新构造市场历史。

**Interpretation = BLOCKED。Trading = BLOCKED。** 等待明确授权。现在不准设计下一层。

**Research Line — BACKLOG**（可从本带取状态，不得改钟、不得写回主观字段）：

- 盘整 = 中枢递归
- 历史 HTF 锚点 → B1 命运
- OF → 笔端点 / HHI-push / OF → B2
- 跨周期、SMC detector、Candidate Setup + MFE/MAE

---

## 钟（复用，不新发明）

- 15m / 1H resample：`chan_fractal_of.clock.resample_bars`
- leftover：`chan_htf_hist_anchor.replay.replay_htf_hist` + `leftover_at`
- B1_LOCK：`chan_htf_zs_ltf_b1.replay.replay_ltf_b1_lock`（只作旗标）
- kline OF：`chan_fractal_of.of_window` 的 `delta = 2*taker_buy_base - volume`
- 成交级 OF：`chan_trade_of.trades.snapshot_slice`。缺文件则 `of_trade_status=not_loaded`

硬门：时刻 `t` = 该根 15m **已收盘** close。HTF 只用 `HTF.close < t`。OF 窗口上沿严格 `< t`。

---

## 完整性验收（不是 Edge）

| 门 | 要求 |
|----|------|
| C0 | 约 90 天 15m 连续（缺口须记账） |
| C1 | leftover `T_ZS_COMPLETE < t`，改写轨不得当锚点 |
| C2 | 15m 结构来自已闭合前缀 |
| C3 | OF `of_window_end <= t` 且若有 `T_FX_VISIBLE` 则 `of_window_end <= T_FX_VISIBLE` |
| C4 | `smc_state` 恒为 `UNDEFINED` |
| C5 | 禁止键不出现 |
| C6 | 同一 `t` 可重放、字段一致 |

PASS 后本 ID 冻结为事实层底座。解释 / Setup / 收益 overlay 一律新 ID、同一条带。

---

## 默认组合

```
symbol:   BTCUSDT-PERP
HTF:      1H
LTF:      15m
window:   90d  (2026-05-21 10:39 UTC → 2026-08-19 10:38 UTC)
data:     nautilus_mm/data/chan_2buy_of/BTCUSDT-PERP/
```

4H 不进 v1。不准换周期救完整性。

---

## TAPE-90D-1H-15M

Log: `logs/chan_desk_replay/CHAN_DESK_REPLAY_001/TAPE-90D-1H-15M/`

```
CHAN_DESK_REPLAY_001 / PASS / STATE_TAPE_OK
```

| 门 | 结果 |
|----|------|
| C0 | PASS n_15m=8641 span_days=90.00 gaps=0 |
| C1 | PASS leftover `T_ZS_COMPLETE < t` |
| C2 | PASS 已闭合 15m 前缀 |
| C3 | PASS OF 窗口上沿 ≤ t 且 ≤ T_FX_VISIBLE |
| C4 | PASS smc_state=UNDEFINED |
| C5 | PASS 无 allow/entry/stop/MFE/of_support/B2 |
| C6 | PASS 8641 个 t 唯一，探针可重放 |

`n_b1_lock=8`：稀疏结构事件索引，不是交易机会，不是 Setup。`of_trade_ok=8641`。窗口 `2026-05-21 10:45 UTC → 2026-08-19 10:45 UTC`。

```
Fact Layer:            FROZEN FACT BASELINE
Interpretation Layer:  BLOCKED
Trading Layer:         BLOCKED
```

≠ Edge。不准改 Tape。不准预设计 Setup ID。等待明确授权。
