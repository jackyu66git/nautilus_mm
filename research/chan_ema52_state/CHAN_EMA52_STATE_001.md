# CHAN_EMA52_STATE_001

```
Track:     Market State × EMA52 回撤位置（WHERE_001 已封存）
Phase:     锁 State → 只在 Trend 里分桶 → 结构命运对照
Input:     同一 1m 窗口。1H 缠论状态 × 1H EMA52
```

WHERE_001 数字不可变。本枪不改 EMA 参数，不加 OF / MACD / 三买，不做阈值搜索。

问的不是「EMA52 是不是支撑」。问的是：

位置效应有没有被 Market State 调制？

```
先锁 State（1H 中枢，在线）
  RANGE      收盘在当前 living 中枢 [zd, zg] 内
  TRANSITION 收盘已离开盒子，但当根 K 仍与盒子重叠
  TREND_UP   当根完全在 zg 上方
  TREND_DOWN 当根完全在 zd 下方
        ↓
只在 TREND_* 开回撤事件。RANGE 穿越不准进对照。
        ↓
摆动确认 T_SWING_VISIBLE 当时必须已是 Trend
        ↓
Checkpoint = 第 4 根 1H（与 WHERE 相同，不准改）
  CROSS / NEAR / MID / FAR   （NEAR_K=0.5 ATR，AWAY_K=1.0 ATR）
        ↓
结构命运（不是涨跌）
  RESUME          原方向创新高/低
  NEW_ZS          新 living 中枢出现
  RANGE_REENTRY   回到 RANGE
  REVERSE         Trend 反向
```

核心对照：`Trend + NEAR` vs `Trend + FAR`。不是无状态的近 vs 远。

若只有 Trend 下才有对照，EMA52 的定位是「特定状态下的回撤区域」，不是普适支撑/压力。
