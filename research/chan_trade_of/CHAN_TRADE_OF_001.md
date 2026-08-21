# CHAN_TRADE_OF_001

```
Experiment:     CHAN_TRADE_OF_001
Status:         Phase 0 = PASS / NEW_DIMENSION
                Phase 1 = PASS / NEW_DIMENSION_CONFIRMED
                Phase 2 = FAIL / CONDITIONAL_MECHANISM
                ≠ NEW_EDGE。不准 B1/B2 HTF SMC 5m absorption 交易层
Type:           信息源实验。不是 Alpha。不是 detector
Structure:      15m Fractal ONLY。forming 沿用 STRATA；T0 = T_FX_VISIBLE
OF:             同期 aggTrades
保留:           价层分布（HHI）、价格推进（push）
丢弃:           加总 delta（与 Kline 同一因子）、speed（volume 改写）
NEW_DIMENSION ≠ NEW_EDGE。Phase 1 已跑。不准吸收定义 / 5m / 回测。
```

Phase 0 固定 15m，不跑 5m。不是因为 15m 最好，而是要和已完成基线严格可比。只替换 OF：

```
15m Fractal                 15m Fractal
    ↓                           ↓
1m Kline taker-flow         aggTrades
    ↓                           ↓
CHAN_BI_OF_STRATA_001       CHAN_TRADE_OF_001
    ↓
NO_GRADIENT
```

若出现新信息，归因只能是 OF 信息源升级，不是时间周期变了。  
禁止一开始同时改两个变量（5m + aggTrades）。

### Phase 0 实验矩阵

| | Kline OF | aggTrades |
|--|----------|-----------|
| 15m | 已完成：NO_GRADIENT | **现在测试** |
| 5m | 已有弱代理研究边界 | 暂不测试 |

15m + aggTrades 若仍无独立维度，不急着换 5m。  
若出现明显新维度，再决定是否做 5m + aggTrades——那时问的是尺度稳定性，不是在失败结果上换周期找阳性。

```
Chan 15m
   │
   └── forming fractal
          │
          ▼
      aggTrades
      ├── price
      ├── quantity
      ├── aggressor
      ├── price-level distribution
      └── trade speed
```

授权后的顺序（不准跳）：

1. 时间 / 因果完整
2. aggTrades 重建的 delta 与 Kline delta 对齐
3. 看 price-level distribution
4. 看速度 / 到达过程
5. 看这些维度是否只是 delta 的另一种表达
6. 最后才允许谈 absorption / exhaustion / sweep

Absorption 是待验证机制，不是 detector。禁止：看起来像吸收 → 定义 absorption → 调阈值 →「发现 Edge」。

---

## STRATA 的正确表述（不可变数字，收窄语义）

| ID | 数字 | 只能写成 |
|----|------|----------|
| CHAN_BI_OF_STRATA_001 | FAIL / NO_GRADIENT | 15m 结构 + **1m Kline taker-flow proxy** 无端点后独立价格增量 |
| CHAN_BI_OF_STRATA_005M_001 | FAIL / MFE_ONLY | 同一代理，5m 结构。MAE 仍未改善 |
| CHAN_BI_OF_STRATA_001M_001 | FAIL / NO_GRADIENT | 同一代理，1m 结构 |

不准写成：OF 没有价值。  
不准再开 `CHAN_BI_OF_STRATA_*` 换 TF。那是继续研究同一个弱代理。

Kline 实验留下的事实仍然有效：

- 该代理对「最终成笔」有中等排序信息（`CHAN_FX_BI_OF_001`）
- 该代理对「确认端点之后的路径」没有经济增量（STRATA 三尺度）

所以下一层换 **对象**，不换周期。

---

## 树

```
                 缠论
            几何分型 / 笔
                  │
          ┌───────┴────────┐
          │                │
      结构真值          成交级 OF
    （已冻结时钟）     （本 ID 的对象）
          │                │
          └───────┬────────┘
                  ↓
             微观质量
```

禁止：

```
delta + imbalance + absorption + exhaustion + sweep + L2 + CVD
        ↓
找最好看的组合
```

完整 OF 是独立研究对象。一次只升一层信息。

---

## Phase 0 正式结论

真正保留的不是「aggTrades 比 Kline 更细」，而是：

```
Kline delta
    ↓
只能看到买卖主动成交的总量

aggTrades
    ↓
同样的 delta
    ├── 价层如何分布      ← HHI
    └── 成交产生了多少实际价格推进  ← push
```

| 量 | 正式判定 |
|----|----------|
| 加总 delta | 无新信息。不要和 Kline delta 当两个因子 |
| speed | 无新信息。R²=0.85，是成交量/窗口长度的改写。不再包装成 OF 因子 |
| HHI | 新维度。R²=0.12，同量同振幅 CV=1.92 |
| push | 新维度。R²=0.01，同桶 CV 很大 |

可以出现：卖方主动成交量相近，A 集中、push 小（价格打不动），B 分散、push 大（价格被推进）。这是 Kline delta 看不到的。

研究问题从「卖了多少」变成「同样卖了这么多，为什么价格推进程度不同」。接近 effort/result，**现在不要叫 absorption**。尚未证明「effort 大 + result 小」是稳定、稀疏、可复现的吸收。目前只能说：aggTrades 提供了 Kline delta 之外的 price-level / price-response 信息。

---

## Phase 1（CONTRACT FROZEN / BLOCKED）

NEW_DIMENSION ≠ NEW_EDGE。不准提前讨论吸收。

```
15m Fractal
      │
      ▼
forming window
      │
      ▼
aggTrades
      │
      ├── delta ────── 已知，Kline 可还原
      ├── speed ────── 基本是 volume 的表达
      │
      ├── HHI ──────── NEW DIMENSION
      └── push ─────── NEW DIMENSION
```

只问：

> 控制住成交量 / delta 后，HHI 与 push 之间是否仍然存在稳定的结构关系？

成立 → 「成交分布」与「成交结果」是两个不同维度。  
不成立 → HHI 可能只是漂亮、没有机制意义的描述。

判读顺序（不准跳、不准猎分位）：

1. 因果：只用 `t < T_FX_VISIBLE`
2. 条件化：在相近 delta / volume 环境下比较
3. HHI → push：看关系是否稳定，不是找最佳分位
4. 分桶一致性：避免整体相关只来自极端样本
5. 稳定性：不同事件、不同成交量环境是否仍成立

三个可能结论：

| 结果 | 含义 |
|------|------|
| 稳定关系 | NEW_DIMENSION CONFIRMED。可以继续研究机制 |
| 只在某些振幅/成交量环境成立 | 条件性维度。不能直接叫独立机制 |
| 关系消失 | HHI 统计上不同于 delta，但没有形成有意义的 OF 结构 |

继续锁死 15m。Phase 0 已经完成干净的变量替换；换 5m 会把周期差异混进来。

```
CHAN_TRADE_OF_001 / Phase 1 = PASS / NEW_DIMENSION_CONFIRMED
≠ NEW_EDGE
```

## SMOKE-60D-15M Phase 1

同一 1957 个 15m forming 事件。3×3 条件化 `|delta| × volume`，不猎分位。

| 门 | 结果 |
|----|------|
| C1 | PASS leak=0 |
| C2 | PASS 8/9 格 n≥40（V1D3 n=33 不进一致性） |
| C3 | PASS 残差 Spearman(HHI,push)=**−0.323**（原始 −0.106）。线性 inc_R²≈0 |
| C4 | PASS 8/8 合格格同号（全负） |
| C5 | PASS 半样本 −0.28/−0.33；底/顶 −0.32/−0.33 |

符号：HHI 越高（更集中），push 越小。这与「同样的量，集中时打不动」同方向，**仍不叫 absorption**。

inc_R²≈0：这是秩关系，不是线性解释力。不能当成预测因子或 Edge。

低 `|delta|` 两格（V2D1、V3D1）ρ≈0，关系主要在中高 `|delta|` 环境仍同号。按预冻规则仍是 CONFIRMED（符号一致），不是换规则去找阳性。

Log: `logs/chan_trade_of/CHAN_TRADE_OF_001/SMOKE-60D-15M/PHASE_1_INVENTORY.txt`

---

## Phase 2（FAIL / CONDITIONAL_MECHANISM）

机制验证，不是交易验证。NEW_DIMENSION_CONFIRMED ≠ 机制已钉牢。  
不准叫 absorption。不准接 B1/B2。三种出口均不进交易层。

仍用：15m Fractal + 同一 forming window + aggTrades。n=1957。不改结构对象。

```
aggTrades
   │
   ├── effort：|delta| / volume
   ├── distribution：HHI
   └── result：push
             ↓
       HHI ↑ → push ↓
```

| 门 | 只问 | 结果 |
|----|------|------|
| M0 | Phase 1 控制仍在 | PASS ρ_resid=−0.323 leak=0 |
| M1 | 时间三分位 | PASS −0.281 / −0.274 / −0.344 |
| M2 | 底 / 顶 | PASS −0.318 / −0.327 |
| M3 | 低 / 中 / 高成交强度 | **FAIL** −0.023 / −0.387 / −0.630 |
| M4 | 替代解释（range + 1/n_levels；丢 p95 极端） | PASS 残差 −0.322；丢极端 −0.256 |

M3 是出口原因。低 effort 格 ρ≈0；中/高格同号且变强。关系只在特定成交强度成立，不能泛化成独立机制。

M4 未把残差吃掉：控制 mid_range 与 1/n_levels 后 ρ 几乎不动（−0.323 → −0.322）。HHI 与 1/n_levels 的 Spearman=0.767 是集中度定义本身，不是 HHI→push 的替代解释。丢 p95 |delta| 与 mid_range 后仍 −0.256。因此 **不是 ARTIFACT**。

| 预冻出口 | 本跑 |
|----------|------|
| MECHANISM_STABLE | 未达。M3 失败，不能写成 effort/result mismatch |
| **CONDITIONAL_MECHANISM** | **成立。只在中/高 effort 环境** |
| ARTIFACT | 未达。M4 未吸收残差 |

Phase 1 的 CONFIRMED 数字仍成立。Phase 2 把它钉成：有维度、有条件相关，没有可泛化机制。

下一枪不是 Phase 3。见 `CHAN_FX_BI_TRADE_OF_001`：同一 15m 分型，完整 OF × 笔端点。**FAIL / NO_INCREMENT**。

```
CHAN_TRADE_OF_001 / Phase 2 = FAIL / CONDITIONAL_MECHANISM
≠ NEW_EDGE
不准 B1/B2 HTF SMC 5m absorption 交易层
```

Log: `logs/chan_trade_of/CHAN_TRADE_OF_001/SMOKE-60D-15M/PHASE_2_INVENTORY.txt`

---

## 门（Phase 0 / 1，授权后才跑）

| 门 | 只问 | FAIL 则 |
|----|------|---------|
| T0 | 时间因果完整；无未来成交 | 停 |
| F1 | aggTrades 重建 delta ≈ Kline delta | 数据不可用，停 |
| F2 | 价层分布 / 速度 / 推进效率 **不是** `delta + volume + 价格振幅` 的同义改写 | 停。承认：更细，但本窗口没有新信息 |
| F3 | 身份：visible 之后不准回写 forming | 停 |

F2 的正例（才值得继续）：

```
同样的总成交量
相近的价格振幅
但是：
  成交集中位置
  成交速度
  主动成交的价格推进效率
明显不同
```

这时才有资格问：为什么同样的卖方主动成交，有些能打穿价格，有些打不动。  
那是成交级 effort/result，不是用 OHLCV 猜。

F2 过 ≠ Edge。≠ absorption 检测器。≠ 可开经济链。

---

## Forbidden

- Phase 0 跑 5m / 同时跑多 TF
- 再开 Kline taker-flow 的 STRATA 换 TF
- L2 / order book / sweep-of-book
- 特征堆叠猎金、阈值、classifier
- B1/B2 当特征；HTF；SMC
- Nautilus 下单、Success / WR / PF / Entry
- 用确认后成交重写 forming

---

## Default combo

```
symbol:     BTCUSDT-PERP
structure:  15m Fractal ONLY
OF:         同期 aggTrades
window:     原 STRATA 15m forming；T0 = T_FX_VISIBLE
5m:         不动
L2:         无
```

```
CHAN_TRADE_OF_001 = Phase 0 DONE
decision:       PASS
kind:           NEW_DIMENSION
T0 PASS · F1 PASS · F2 PASS · F3 PASS
5m BLOCKED · L2 BLOCKED · absorption 仍不是 detector
```

SMOKE-60D-15M：n_fx=1957 leak=0

| 门 | 结果 |
|----|------|
| T0 | PASS leak=0 empty=0 retracted=0 |
| F1 | PASS Spearman(trade Δ, kline Δ)=1.000，中位相对误差 ~0。总和就是 Kline delta |
| F2 | PASS 新维度 = 价层 HHI、推进效率。速度不是（R²=0.85，是 volume 的另一种表达） |
| F3 | PASS forming 未用 T_FX_VISIBLE 之后的成交 |

F2 细节（对 `|delta| + volume + mid_range`）：

| 量 | max \|ρ\| | OLS R² | 同量同振幅内 CV | 判定 |
|----|-----------|--------|-----------------|------|
| speed | 0.872 | 0.848 | 0.387 | 同义改写 |
| hhi | 0.689 | 0.121 | 1.915 | 独立维度 |
| push | 0.521 | 0.008 | 9.533 | 独立维度 |

同样的总量、相近振幅时，成交集中度与价格推进效率仍明显散开。这才有资格问 effort/result。  
PASS ≠ Edge。不准定义 absorption。不准开 5m。不准开经济链。

Log: `logs/chan_trade_of/CHAN_TRADE_OF_001/SMOKE-60D-15M/`
