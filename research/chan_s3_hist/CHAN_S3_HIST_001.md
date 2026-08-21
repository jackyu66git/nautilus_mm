# CHAN_S3_HIST_001

```
Track:     Historical / Statistical Diagnostic。不是 OOS。不是 Recheck
Phase:     冻结 S3 定义下的长历史出现率与 0.5R/24h 路径
Input:     1m BTCUSDT-PERP，T_3 严格早于 CHAN_DESK_REPLAY_001 起点
```

本枪窗口缩到 **Tape 前 1 年**（外加 3 个月 burn-in）。5 年 15m 流式扫描约 18 万根，50 分钟只走完 16%，不可做诊断。1 年仍按 8 个 S3 / 90 天的密度，预期 n_S3 刚过闸 MIN_N=30。不是为了看结果才改窗，是计算不可行。
本枪不改三买定义，不把 S3 搞多，不定 16 该不该改。
本枪不能当最终 confirmation。0.5R 是在 90 天窗上选的，用到更早历史上只是诊断。

```
                 CHAN_B3
                    │
          ┌─────────┴─────────┐
          │                   │
     Original OOS        CHAN_S3_HIST_001
       8 → 16              大样本 · 向后
          │                   │
       G0 WAIT             值不值得等
          │                   │
          └─────────┬─────────┘
                    ↓
             V2_RECHECK（仍要 n_S3≥16）
```

## 窗口（冻结，不搜索）

| 钟 | 值 |
|----|----|
| 数据起点 | 2025-02-21 00:00 UTC（3 个月 burn-in） |
| 事件计入 | `2025-05-21 10:39 ≤ T_3_VISIBLE < 2026-05-21 10:39` |
| 排除 | Fact Tape 90 天（定义 / 选 0.5R） |
| 排除 | 2026-08-19 之后（留给 Recheck 前向 OOS） |

定义 = `CHAN_3RD_POINT_001`。Entry / Stop / 0.5R / 24h = V2 合同。无 EMA / OF / ATR。
Regime = 日历年。不准另搜桶。

B3 分表必报。等不等的闸只看 **S3**。

## 预注册闸（S3，已成交）

```
n = 成交 S3（非 SKIP/CENSOR）

WORTH_WAIT
  n ≥ 30
  avg R > 0
  符号翻转 perm p（H1: mean R > 0）≤ 0.05
  日历年中 n≥8 的年份，过半数 avg R > 0（若没有这样的年份则跳过本条）

NOT_WORTH_WAIT
  n ≥ 30
  avg R ≤ 0
  perm p > 0.10
  0.5R@24h hit < 0.40

INCONCLUSIVE  其余
```

两种结果都 **不取消 G0**。HIST 不是 OOS，不能替代 Recheck。
NOT_WORTH_WAIT 只说明：继续等 16 的先验很弱，不是偷看 9…15 的 PnL。

PERM_N=10000，seed=1。

## 冻结结果

`INCONCLUSIVE / THIN`。not_oos。G0 不动。

Tape 前 1 年：n_S3=27（成交 27），低于预注册 MIN_N=30，所以不能判 WORTH_WAIT / NOT_WORTH_WAIT。

| | n | WIN/LOSS/TIME | hit24 | avg R | perm p |
|--|---|---------------|-------|-------|--------|
| S3 | 27 | 10 / 5 / 12 | 0.37 | −0.139 | 0.88 |
| B3 | 24 | 11 / 4 / 9 | 0.46 | +0.024 | — |

S3 / 90d = 6.66，比定义窗的 8 更稀。空窗 p50=266h，max=907h（≈38 天）。
2025 avg R=−0.11，2026 至 Tape 起点 avg R=−0.18。方向都不正。
n 差 3 个就到 30，**不准事后把 MIN_N 改成 27 来改判**。不准因此取消 G0。

## 禁止

- 改 S3 定义、换周期、把事件搞多
- 把本枪写成 OOS PASS / Economic PASS
- 用本枪取消或提前跑 Recheck
- 偷看当前等待窗 9…15
- Cap Stop、定 5/10/15%、加 EMA/OF
- 只报 B3
