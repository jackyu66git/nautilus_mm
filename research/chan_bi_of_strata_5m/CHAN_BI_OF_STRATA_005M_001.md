# CHAN_BI_OF_STRATA_005M_001

```
Experiment:     CHAN_BI_OF_STRATA_005M_001
Type:           15m 同构复制。只改结构 TF 15m → 5m
Predecessor:    CHAN_BI_OF_STRATA_001 FAIL / NO_GRADIENT（不可变）
Scale:          5m FX / BI + 1m OF
Replay:         只读。不准重新设计
Scope:          同一 kline taker-flow 代理的尺度复验。不是完整 OF。
```

唯一变化：结构对象从 15m 换成 5m。其余冻结。

```
5m 几何分型
    ↓
确认成为 5m 笔端点
    ↓
T_BI_SURE
    │
    └── 回看 T_FX_VISIBLE 之前的 1m OF
                ↓
             OF 五分位
                ↓
       MFE / MAE / 4·8·16 根 5m
                ↓
          扣费 expectancy
```

| 项目 | 15m 已完成 | 5m 本 ID |
|------|------------|----------|
| 结构 | 15m FX / BI | 5m FX / BI |
| OF | 1m | 1m |
| OF 截止 | < T_FX_VISIBLE | 完全相同 |
| 分桶 | 五分位 | 五分位 |
| 结果 | MFE / MAE / 4/8/16 | 完全相同 |
| 阈值 / classifier | 无 | 无 |
| B1/B2 HTF SMC | 不用 | 不用 |

```
Experiment:     CHAN_BI_OF_STRATA_005M_001
decision:       FAIL
kind:           MFE_ONLY
15m predecessor: CHAN_BI_OF_STRATA_001 FAIL/NO_GRADIENT 不可变
S0 PASS · S1 PASS · S2 FAIL · S3 NOT_RUN
```

## SMOKE-60D-5M

Log: `logs/chan_bi_of_strata_5m/CHAN_BI_OF_STRATA_005M_001/SMOKE-60D-5M/`

```
S0 PASS   leak=0  n_ep=834  bottom=417  per_q≈83
S1 PASS
S2 FAIL   MFE_ONLY：16 根收益中位数 Q1→Q5 单调（ρ=1.00），MAE 没有改善（ρ=+0.30）
          MAE Q1→Q5  26.9  16.9  20.9  19.7  29.7 bps
          ret_16     -6.0  -5.5  -2.5  -1.8  +0.0 bps
          扣 8bps 后 ret_16 全负（Q5 仍 −8.0 bps）
S3 NOT_RUN
decision  FAIL
```

对比 15m：两边都不是「MAE 随 OF 质量改善」的稳定梯度。  
5m 的 16 根收益排序幅度约 6bps，小于往返费用，不称 Edge。  
不准扩其它 TF。不准用 B1/B2 / HTF / SMC 解释。OF 作为独立交易层在这两个结构尺度上收口。
