# CHAN_2ND_POINT_FATE_001

```
Track:     二买/二卖。独立于三买 HOLD
Phase:     在线定义 + Fate Census。无 EMA / OF / Trend Age
Input:     同一 90 天 1m 窗口。15m。不准扩窗、不准改定义
```

三买线不动。不准拿二买去救 EMA52。

引擎二买（`find_second_bsp`）：

```
一买/一卖（离开笔 + MACD 柱面积背驰）
        ↓
反向一笔确认
        ↓
再一笔不破一类高低点          T_2_VISIBLE
        ↓
Fate（与三买对称口径，但失效锚是一类点，不是中枢盒子）
  RESUME    原方向再创新高/低
  REVERSE   收盘打穿一类低/高
  REENTRY   仅当 T_2 时已在中枢外，之后收盘回到 [zd,zg]
```

二买经常发生在中枢内/附近。T_2 已在盒子里时，REENTRY 不适用，不当失败。
失效锚 = 一类高低。冻结。不准为后续统计方便换成中枢盒子。

Census（冻结）：57 离开 → 34 NO_FIRST → 14 BROKE_FIRST → 9 B2/S2。
Fate：RESUME=9 REENTRY=0 REVERSE=0。
`hours_to_fate` = confirmation → fate bar latency。≠持仓 / 趋势时长。
分布：0.25h×5，0.5h×1，1.75/2.0/3.75 各1。5/9 下一根 15m 即 Fate。
p50=0.25h。≠二买比三买快一倍。≠二买可持有多久。
BROKE_FIRST=14 ≠ 二买失败。9/9 ≠ 比三买更强，≠ 成功率 100%。
HOLD。不准挖一买。不准开生命周期。

不准放宽「必须先有一类」。不准优化背驰。
