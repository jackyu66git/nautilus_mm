# CHAN → LIVE

```
Repo:      https://github.com/jackyu66git/nautilus_mm
Not:       nautechsystems/nautilus_trader
           freqtrade/freqtrade
Active:    G0 WAIT n_S3>=16
Done:      G-R  CHAN_B3_R_CENSUS_001 = NO_TAIL / SHAPE_OK
Locked:    G0b = N/A · G1–G9
```

这是从冻结 B3/S3 到实盘的**唯一总计划**。Gate 未给出 PASS / FAIL / FAMILY_SPLIT / NO_TAIL / LONG_TAIL 时，不准重新规划，不准临时加实验。

官方 NautilusTrader 只在 G6 Paper 以后作为执行引擎。本仓库是研究合同与离线枪。

```
G-R  R Distribution Census
        │
        ├── NO_TAIL  → G0 WAIT n_S3>=16 → G1 Recheck 0.5R
        └── LONG_TAIL → G0b Risk Distance Gate（NO TRADE，不 Cap Stop）
                         → G0 WAIT → G1
G1 PASS → G2 OOS → G3 Economic → G4 Robustness → G5 Strategy Freeze
      → G6 Paper → G7 Shadow → G8 Small Live → G9 Scale
```

---

## 状态表

| Gate | 状态 | 下一动作 |
|------|------|----------|
| G-R R Census | **DONE** `NO_TAIL` | 无资格开 G0b |
| G0 自然样本 | **ACTIVE WAIT** | S3 ≥ 16 才 `CHAN_B3_V2_RECHECK` |
| G0b Risk Distance | N/A | 形状闸未触发。不准另定 5/10/15% |
| G1 Recheck | LOCKED | n_S3≥16 |
| G2–G9 | LOCKED | 仅当前一格 PASS（或 G1 的 SPLIT 旁路） |

G-R 冻结数字（n=20，R_pct = |Entry−Stop|/Entry）：

| | p25 | p50 | p75 | p90 | p95 | max |
|--|-----|-----|-----|-----|-----|-----|
| all | 1.36% | 2.12% | 2.40% | 4.04% | 4.38% | 6.19% |
| B3 | 0.96% | 1.54% | 2.22% | 2.34% | 2.40% | 4.38% |
| S3 | 1.38% | 2.35% | 3.79% | 4.04% | 4.04% | 6.19% |

形状：p90/p50=1.91、p95/p50=2.07、max/p50=2.92。均低于闸（2.5 / 3.0 / 5.0）。
假设中的 12%–31% 长尾**没有出现**。最大 Raw R 是 6.19%（一笔 S3，TIME_EXIT）。
0.5R 作为价格百分比：p50≈1.06%，max≈3.09%。不是同一厘米，但未构成预注册的异常交易域。
不准把这次 NO_TAIL 改写成「可以 Cap Stop」。Stop 仍是盒沿。

---

## 硬原则

- Raw R 定义不变：`Entry → 中枢反向盒沿`（B3=zd，S3=zg）。Entry = T0 确认后下一根 15m 开盘。
- **不要 Cap Stop。** 拒绝异常交易，不把 Stop 从 90 改成 95。
- 结构有效 ≠ 交易距离有效。
- 不定 5% / 10% / 15% 作为交易阈值。那是参数优化。
- B3 与 S3 都做。不准只做 B3。
- B1/B2 永久 HOLD，直到独立新理由。
- EMA52 / OF / Trend Age / ATR 冻结。G5 且 V1 已有经济 Edge 之后，才允许一次一个独立 ID。
- 不准偷看 n_S3∈[9,15]。

锁定合同（G-R 之后仍有效，除非 G0b 增加 SKIP）：

| 槽 | 锁定 |
|----|------|
| Entry | 确认后下一根 15m 开盘 |
| Stop | 中枢反向盒沿。不 Cap |
| TP | 0.5R Candidate |
| Time Exit | 24h |
| 1R | Entry 到结构 Stop，不是 ATR |
| 方向 | B3 + S3 |

---

## G-R  `CHAN_B3_R_CENSUS_001`

只统计冻结 20 个 B3/S3：

```
R_pct = |Entry - Stop| / Entry
```

报 p25 / p50 / p75 / p90 / p95 / max。对照 R_pct vs MFE vs TIME。不改策略。

长尾用**分布形状**，不用价格百分比：

```
LONG_TAIL  若  p90/p50 ≥ 2.5  或  p95/p50 ≥ 3.0  或  max/p50 ≥ 5.0
NO_TAIL    否则
```

**NO_TAIL**：G0b = N/A。Active → G0 WAIT。

**LONG_TAIL**：解锁 G0b。有效域 `R_pct ≤ 本枪冻结的 p90`。超出 → SKIP / NO TRADE。Stop 仍是盒沿。不搜索 p75 vs p90，不搜索 5/10/15。然后 Active → G0 WAIT。Recheck 带上 SKIP。不准用 Skip 改成只做 B3。

---

## G0 WAIT

n_S3 < 16 → NOTHING。n_S3 ≥ 16 → 自动一次 `CHAN_B3_V2_RECHECK`，不再开会。

## G1 Recheck

只测 0.5R。五条同时：B3 正期望；S3 avg R > −0.10；合样本正期望；非单笔驱动；无新变量。PASS → G2。FAMILY_SPLIT → 才允许不对称研究（仍不是只做 B3）。FAIL → 停交易线。

G1 集 = 从现有研究窗起点到第 16 个 S3 的 `T_3_VISIBLE` 为止，全部 B3/S3（含原来 20 笔）。
G1 cutoff = 第 16 个 S3 的 `T_3_VISIBLE`。

## G2 OOS

`T_3_VISIBLE` **严格晚于** G1 cutoff。只向前。禁止回头挖 2026-05-21 之前。无调参。只有 PASS / FAIL。

## G3–G9

G3 Economic 才加 Binance fee / slippage / funding / latency。此前一切 ≠ Economic PASS。
G4 Robustness：固定策略，时间 / 波动 / 执行扰动 / 分 family / 回撤。
G5 `CHAN_B3_STRATEGY_V1` 冻结。改策略 = 新 ID。
G6 Paper 接 NautilusTrader（复用 `src/nautilus_mm/event_ledger.py` 思路，不把 MM_EDGE 微观对象塞进结构策略）。
G7 Shadow = 真实行情 + 模拟单。
G8 Small Live = 极小风险验成交。
G9 Scale = 仅当与回测 / OOS 无系统性偏离。
