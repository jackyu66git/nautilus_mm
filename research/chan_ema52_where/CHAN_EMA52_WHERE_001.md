# CHAN_EMA52_WHERE_001

```
Track:     1H 趋势回撤 × EMA52 动态支撑/压力（最高优先级）
Phase:     Layer 1 only。定义 + 因果审计 + Census + 近/远对照
Input:     与 Fact Tape 同一 1m 窗口。1H EMA52。不准改窗口
```

EMA52 是 WHERE，不是预测器。不准把「EMA 附近 + 后来上涨」写成 Setup。

MACD 不进本 ID。第三类买卖点不进本 ID（不准用均线定义三买）。
`CHAN_3RD_POINT_001` Phase 1 数字冻结；Phase 2 暂停。

```
1H 趋势已可见
        ↓
离开 EMA52（≥ 1 ATR）
        ↓
1H 摆动高/低确认                         T_SWING_VISIBLE
        ↓
回撤中第一次贴近当前 EMA52               T_NEAR_VISIBLE
        ↓
其后先出现：创新高/低 = RESUME
           收盘跌破/升破 EMA = BREAK
```

贴近 = 当根 low/high 进入 `EMA ± 0.5 ATR`，且当根收盘未穿过 EMA。
对照钟 = 摆动确认后第 4 根 1H：当时已 NEAR vs 仍 FAR，再看其后 RESUME/BREAK。
不准用回撤结束结果来定义是否「到过 EMA」。

参数冻结，不准为了对照去搜：EMA span=52，ATR=14，AWAY=1.0 ATR，NEAR=0.5 ATR，趋势确认=连续 8 根在均线正确侧。

---

## 封存语义（数字不可变）

`FAIL / NO_STATE_CONTRAST` **不是**「EMA52 没用」。

本 ID 问的是无状态的距离：回到均线附近 vs 回撤仍远离。在该定义下没有足够状态对比。

排除的是：把 EMA52 当成**普适**支撑/压力线。

不排除、且必须分开的两种 Market State：

```
Trend / Expansion → Pullback → EMA52     动态支撑/压力候选
Range / Center    → EMA52 穿越           中枢内均值穿越，不是失败样本
```

中枢震荡里反复穿越均线，不能当本 ID 的负面证据，也不能写进后续识别的失败案例。

下一步若做 EMA，研究的是「不同 Market State 下含义是否改变」，不是继续榨距离。不准改本 ID 参数把震荡样本剔掉来翻盘。

