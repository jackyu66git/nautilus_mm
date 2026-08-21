# CHAN_BI_OF_STRATA_001M_001

```
Experiment:     CHAN_BI_OF_STRATA_001M_001
Type:           同构复制。只改结构 TF → 1m
Predecessor:    15m FAIL/NO_GRADIENT、5m FAIL/MFE_ONLY（均不可变）
Scale:          1m FX / BI + 1m OF
```

唯一变化：结构对象改成 1m。其余冻结。

```
1m 几何分型
    ↓
确认成为 1m 笔端点
    ↓
T_BI_SURE
    │
    └── 回看 T_FX_VISIBLE 之前的 1m OF
                ↓
             OF 五分位
                ↓
       MFE / MAE / 4·8·16 根 1m
                ↓
          扣费 expectancy
```

不准改已关闭的 15m / 5m ID。不准 B1/B2、HTF、SMC、阈值、classifier。

## SMOKE-60D-1M

```
decision=FAIL  kind=NO_GRADIENT
n_bars=86400  n_ep=3964  n_bottom=1982  per_q≈397
S0 PASS  leak=0
S1 PASS
S2 FAIL  MAE ρ=+0.30  mae_steps=2/4
         ret_16 ρ=−0.60（方向甚至反了）
S3 NOT_RUN
```

扣 8bps 后 Q1→Q5 持有收益全负。三个结构尺度都没有「OF 越好、确认后路径越好」。不称 Edge。不准再扩 TF。
