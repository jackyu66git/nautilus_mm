# Research Architecture — Chan / SMC / MACD / OF / Truth

```
Status:     FROZEN MAP
Fact Layer: FROZEN FACT BASELINE
            CHAN_DESK_REPLAY_001 = PASS / STATE_TAPE_OK
            基准事实层，不是实验结果。Tape / 钟 / 窗口 不准再改
Active:     G0 WAIT。CHAN_TO_LIVE.md
            CHAN_B3_R_CENSUS_001 = NO_TAIL / SHAPE_OK
            CHAN_B3_V2 = HOLD / FAMILY_SPLIT。0.5R = Candidate
            n_S3≥16 才复检。不准新开结构研究
Track:      旧树停机。伪 Alpha 路径已拆
            Fate PASS · Continuation STOP · Location HOLD_NO_SPLIT
            交易线：Raw R 无预注册长尾。恢复等自然 S3
Governance: RESEARCH_MANDATE.md → CHAN_TO_LIVE.md
Paused:     WAITING 是合同。n_S3≥16 之前不复检、不调参、不新开研究
            不准 Cap Stop。G0b = N/A
            旧树 IDLE。EMA52 Frozen · OF Locked Out · Trend Age Attribution only
Frozen:
            命题             弱 continuation = T+1 瞬时扩展。无后续连续扩展证据
            Location         T0 几乎总在盒外。伴生属性 ≠ 独立 Location Signal
                             IN=1/47。不能说中枢外 continuation 更强
            Null Baseline    普通15m mix=0.463。不准重做、不准改成突破
            Persist          CLOSED。H1=+11.1pp H2=−6.2pp。ONE_BAR_ARTIFACT
                             负 delta ≠ 反向 Alpha。不准解释 −6.2pp
            纯 continuation  27/47=0.574。≠ 29/47 Fate
            一类/二买/三买   HOLD。定义冻结
            Trend Age        Candidate / Attribution only。不因本树开启
            EMA52            Frozen。基础 Location 无对照，更不准开
            OF               LOCKED OUT
Closed:     CHAN_EMA52_WHERE_001 = NO_STATE_CONTRAST
            语义：无状态的「近 vs 远」不够。≠ EMA52 没用
            ≠ 普适支撑/压力。震荡穿越不是失败样本
            HTF-ZS-reversal Track 关闭（不再换 Y）
            CHAN_HTF_ZS_LTF_REV_001 = NO_STATE_CONTRAST（位置）
            CHAN_HTF_ZS_EXPAND_LTF_REV_001 = NO_STATE_CONTRAST（扩张）
            EXPAND 事件 n=17 过薄。n_bis=3/5/7/9 无分化
Trading:        LOCKED 到 CHAN_TO_LIVE 状态机。G0 WAIT。G-R = NO_TAIL
Closed:     CHAN_HTF_HIST_ANCHOR_LTF_B1_001
            Phase 0 PASS / HIST_ANCHOR_EXISTS。Q4 FAIL / NO_FATE_CONTRAST
            数字不可变。问法进 Research BACKLOG
            CHAN_HTF_ZS_LTF_B1_001 Phase 0 数字不可变
            living 当前盒子问法关闭。5/5 OUTSIDE
            CHAN_TRADE_OF_001 Phase 2 = CONDITIONAL_MECHANISM
            CHAN_FX_BI_TRADE_OF_001 = FAIL / NO_INCREMENT
            STRATA 三尺度 = 1m kline taker-flow 代理无端点后增量
            15m FAIL/NO_GRADIENT · 5m FAIL/MFE_ONLY · 1m FAIL/NO_GRADIENT
            数字不可变。语义不可扩大成「OF 没有价值」
Replay:     Input = CHAN_DESK_REPLAY_001。不准重新构造市场历史
            时间窗不够 ≠ 改 001
Desk Line:  FROZEN FACT BASELINE
Research:   旧树 IDLE。PENETRATION Census 已停。第二闸另授权。不改本树
SMC:        Meso 行为语言。未开 ID。本带 smc_state=UNDEFINED
MACD:       结构上的动力/效率维度。不占独立中间层。不与 OF 抢位
Closed:     CHAN_LOCATION_001
            CHAN_B1_B2_EARLY_001 OF 预测 B2
Observation Open:  不再找
Signal funnel:     FORBIDDEN（缠论→SMC→MACD→OF 不准）
```

---

## 谁回答什么

| 东西 | 主要回答 | 不是 |
|------|----------|------|
| 缠论 | 在哪里、是什么结构 | 微观进场 |
| SMC | 结构内部发生了什么行为 | 替代大结构；再找关键位 |
| MACD | 这段运动的动力/效率怎么样 | 新的市场结构；独立中间层 |
| OF | 此时真实成交力量怎么样 | 判断大趋势；**不等于** 1m Kline `taker_buy_base` |
| B1/B2 | 结构标签最终是否成立 | 实时预测 |

SMC 是结构语言。MACD 是动力测量。不是完全竞争。  
MACD 有用 ≠ MACD 该占一层。

---

## 结构事件基线（冻结）

```
Structure
   ├── Fate           PASS · B1/B2/B3 HOLD
   ├── Continuation   ONE-BAR ARTIFACT → STOP
   └── Location       HOLD_NO_SPLIT
                      T0 几乎总在中枢外 = 定义伴生属性
                      ≠ 独立 Location Signal
                      不准 ATR 切 OUT · 不准绕 EMA52

另立 Invalidation
   └── PENETRATION_CENSUS  HIERARCHY_CANDIDATE · 停
                          假设「多数很浅」不成立。第二闸另授权

即时价格行为 ≠ 持续方向预测。
中枢内/外 ≠ 当前三类事件的独立解释变量。
已拆掉：结构 → 继续上涨 → 位置 → EMA52。
另立：Invalidation = 确认后反向走到哪里，结构才算被破坏。
```

## 树，不是漏斗

禁止：

```
缠论 → SMC → MACD → OF → Entry
```

那是四层都在当 filter。

冻结为：

```
                 缠论
          Structure / Location
          （B1 语义已含 MACD 背驰）
                  │
          ┌───────┴───────┐
          ↓               ↓
         SMC             MACD
     行为结构           动力效率
          │               │
          └───────┬───────┘
                  ↓
                 OF
          成交层真实性验证
                  ↓
               B1 → B2
```

三层研究压缩：

1. 缠论：Structure / Location / Truth  
2. SMC + MACD：Behavior / Momentum（并列，不是上下游）  
3. OF：Execution Microstructure（成交级对象；Kline taker 只是已关闭的最小代理）  

---

## MACD 钉在结构上

引擎里 B1 已经是：

```
中枢位置 + 向下离开 + check_bi_div（MACD 柱面积）
```

`find_all_bsp` / `check_bi_div` 用的是离开笔 vs 进入段的 `macd_hist`。  
所以 MACD 是缠论买点语义的一部分，不是外加指标，更不是 Meso 层。

允许：在已有笔/离开/分型上读柱面积、背驰。  
禁止：MACD 独立 ID、MACD Location、MACD 当 Observation Open、用 MACD 替代 OF。

MACD 不进 `CHAN_FRACTAL_OF_001` Phase 1（那一层只测 OF）。  
B1 真值里的背驰仍然按源码，不拆掉。

---

## SMC 不是第二套 WHERE

HTF 笔中枢已经是 WHERE。OB/FVG 再找位 = `CHAN_LOCATION_001`。

SMC 只解释已有缠论空间内部：sweep / displacement / MSS / BOS / inefficiency。  
未开 ID。Phase 1 分型 OF 不读 SMC。

---

## 互相验证，不是三个 Entry filter

同一底部可以同时说三件不同的事：

| | 说的是 |
|--|--------|
| SMC | 结构行为变了（扫前低 / displacement） |
| MACD | 运动效率异常（背驰） |
| OF | 成交是否支持这种改变（衰竭 / 承接）。Kline delta 已证明不够；下一层是成交级 |

验证 ≠ 叠加过滤。缺一层不自动否决，先各自计量。

---

## 程序顺序（仍隔离）

Kline taker-flow 链已关。15m 微观 OF 定级完毕。

```
Fact Layer:            FROZEN FACT BASELINE   CHAN_DESK_REPLAY_001
Interpretation Layer:  本条 Candidate 线 CLOSED
                       负结论：HTF leftover + 新 15m 分型 ≠ 结构转折
                       重启必须：新 ID → 新对象 → 新合同 → 新 Replay
                       未授权前不设计、不预研
Trading Layer:         CHAN_B3_BASELINE_V1 已跑。BASELINE_OK ≠ Edge
```

共同因果底座：`logs/chan_desk_replay/CHAN_DESK_REPLAY_001/TAPE-90D-1H-15M/`  
以后任何新实验：`Input = CHAN_DESK_REPLAY_001`。不准重新构造市场历史。

`B1_LOCK` n=8 是稀疏结构事件索引，不是 8 个交易机会，也不是 Setup 出生条件。

`CHAN_SETUP_DEFINITION_001`：观察事件生成器，不是结构 Setup。负结论：HTF 历史空间存在 + 新 15m 分型不足以定义结构转折。不准把此对象优化成 Setup。此对象线关闭。数字不可变。

`CHAN_SETUP_OUTCOME_001`：Replay PASS / OUTCOME_OK。DISSOLVES=2020 REVERSES=321。出生时无 SURE。数字不可变。

`CHAN_SETUP_STRATA_001`：Replay PASS / STRATA_OK。四张预注册单维表无足够稳定 Outcome 分化（DISSOLVES 约 0.84–0.88）。CONTACT_BOX n=61 不升级。不准四维交叉。不准再榨本 ID。数字不可变。

| 步 | 只问 | 结果 |
|----|------|------|
| A PASS | 分型形成过程中 **Kline taker-flow** 有没有因果、有分布差 | 已过（代理层） |
| B FAIL | 该代理与 B1→B2 有差，但不能从 amplitude 拆出 | 买点增量问句关闭 |
| CHAN_FX_BI_OF_001 | 普通分型 vs 笔端点，该代理有没有结构差 | PASS。中等排序，不是识别器 |
| CHAN_BI_OF_STRATA_001 | 该代理分位是否对应端点后经济差 | FAIL / NO_GRADIENT。**仅此代理**（不可变） |
| CHAN_BI_OF_STRATA_005M_001 | 同一代理，5m 结构 | FAIL / MFE_ONLY。MAE 未改善（不可变） |
| CHAN_BI_OF_STRATA_001M_001 | 同一代理，1m 结构 | FAIL / NO_GRADIENT（不可变）。不准再扩该代理的 TF |
| CHAN_TRADE_OF_001 | HHI↑→push↓ 是机制还是统计相关 | Phase 1 CONFIRMED。Phase 2 FAIL / CONDITIONAL_MECHANISM。不进交易层 |
| CHAN_FX_BI_TRADE_OF_001 | 完整 OF 是否比 delta 多提供笔端点结构信息 | FAIL / NO_INCREMENT。15m 微观 OF 定级，停 |
| CHAN_HTF_ZS_LTF_B1_001 | living 当前盒子是否先于 LTF B1 存在 | Phase 0 PASS。5/5 OUTSIDE。问法关闭。数字不可变 |
| CHAN_HTF_HIST_ANCHOR_LTF_B1_001 | 已完成 HTF 的 zg/zd/gg/dd 是否成为未来 LTF B1 的空间记忆 | Phase 0 PASS / HIST_ANCHOR_EXISTS。Q4 FAIL / NO_FATE_CONTRAST。BACKLOG。数字不可变 |
| CHAN_DESK_REPLAY_001 | t 时刻可见世界是什么（FROZEN FACT BASELINE） | DONE / FROZEN。PASS / STATE_TAPE_OK。Input=本带。n_b1_lock=8 ≠ 交易机会 |
| CHAN_SETUP_DEFINITION_001 | 从 Tape 机械判断是否进入观察状态 | CLOSED。CENSUS_OK。观察事件生成器。HTF leftover + 新 15m 分型 ≠ 结构转折。不准优化此对象 |
| CHAN_SETUP_OUTCOME_001 | 观察开始后下一次客观结构事件是什么 | Replay PASS / OUTCOME_OK。DISSOLVES=2020 REVERSES=321。出生时无 SURE。数字不可变 |
| CHAN_SETUP_STRATA_001 | 出生时刻客观状态是否对应不同 Outcome 分布 | PASS / STRATA_OK。NO_STATE_CONTRAST。不准四维交叉。不准再榨。数字不可变 |
| CHAN_HTF_ZS_LTF_REV_001 | living 1H 中枢 A/B/C 是否改变下一根 15m 笔反转率 | CLOSED / NO_STATE_CONTRAST。约 4.1%–5.0%。位置切面关闭 |
| CHAN_HTF_ZS_EXPAND_LTF_REV_001 | living 中枢 n_bis 扩张是否改变下一根 15m 笔反转率 | CLOSED / NO_STATE_CONTRAST。EXPAND n=17 薄。n_bis 3/5/7/9 无分化 |
| CHAN_3RD_POINT_001 | 第三类买卖点能否在线、无未来函数定义 | Phase 1 PASS / CENSUS_OK。n_3=20。漏斗 57 离开→37 回中枢→20。不是 Setup |
| CHAN_LOCATION_CENSUS_001 | T0 相对冻结中枢的位置普查（无 ATR） | PASS / HOLD_NO_SPLIT 封存。IN=1/47。盒内外=定义伴生，≠独立信号。不能说中枢外更强。OUT_HIGH/LOW≠Modifier。不准 ATR/EMA 绕路 |
| CHAN_PENETRATION_CENSUS_001 | 确认后反向 excursion / 冻结锚穿透（无 ATR） | PASS / HIERARCHY_CANDIDATE。不是止损。假设「多数很浅」不成立。MAE-to-end ≠ 失效深度。B1/B2 盒沿不是反向锚。第二闸另授权 |
| CHAN_B3_BASELINE_V1 | 冻结 B3/S3 · T1 open · 盒沿 Stop · 1R TP · 24h TIME | PASS / BASELINE_OK。WIN=4 LOSS=4 TIME=12。mfe24 p50=0.54R。不是 TP 太近也不是 Stop 太紧。TIME_DOMINATED。≠ Edge。不准改 Time/TP/Stop |
| CHAN_B3_EXIT_CENSUS_001 | Exit 几何：R 网格 × 24/48/72h / 至 Stop | PASS / A_SMALLER_TARGET。0.5R@24=11/20，1R@24=4/20。1R any=10/20 p50=24.5h。V2 另授权。−0.58R ≠ Economic FAIL |
| CHAN_B3_V2 | 唯一变量 TP：0.5 / 0.75 / 1.0R | HOLD / FAMILY_SPLIT。0.5R=Candidate 未冻结。B3 支持 S3 不支持。下一格见 CHAN_TO_LIVE G1。不准只做 B3 |
| CHAN_B3_R_CENSUS_001 | Raw R 分布。R_pct=|Entry−Stop|/Entry。不改 Stop | DONE / NO_TAIL。p50=2.12% p90=4.04% max=6.19%。p90/p50=1.91。G0b=N/A。不定 5/10/15% |
| CHAN_3RD_POINT_END_001 | 2 个 REENTRY 在 T_3 前是否已处于不同大级别趋势状态 | PASS / ATTRIBUTION_OK。SHIFT 7/7 RESUME。LATE 3 里 2 REENTRY。两种 LATE 不同。not_proof。不准改三买 |
| CHAN_2ND_POINT_FATE_001 | 15m 二买/二卖确认后的结构 Fate | PASS / FATE_CENSUS_OK。n_2=9（B2=4,S2=5）。9/9 RESUME。5/9 下一根即 Fate。p50=0.25h=判定延迟，≠比三买快一倍。漏斗 57→34→14→9。BROKE_FIRST≠失败。n=9 不准开生命周期 |
| CHAN_EMA52_WHERE_001 | 无状态的「回撤到 EMA52 附近 vs 仍远离」是否改变后续结构命运 | FAIL / NO_STATE_CONTRAST。≠ EMA52 没用。排除普适支撑/压力。震荡穿越不是失败样本。不准改本 ID 翻盘。数字不可变 |
| CHAN_EMA52_STATE_001 | Trend 状态下 EMA52 近 vs 远是否调制后续结构命运 | PASS / SAMPLE_INSUFFICIENT。State 可分。Trend+NEAR n=3。不准并桶/改阈值。无 OF |
| CHAN_3BUY_EMA52_001 | 冻结 20 事件上 15m EMA52 位置诊断 | LOCATION DIAGNOSTIC 有效。不可作 15m 样本扩张结论。9 vs 11 不可变 |
| CHAN_3BUY_15M_UNIVERSE_001 | 冻结定义下 15m vs 1H 独立三买数量 | PASS / UNIVERSE_OK。15m=20 且等于冻结母集。1H=1。无 EMA |
| 空间层 | 历史结构锚点，不是当前盒子，不是 5m OB/FVG | Location_001 已关。living 盒子问法已关 |
