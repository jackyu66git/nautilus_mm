# CHAN_3RD_POINT_END_001

```
Track:     REENTRY 是否是 T_3 之前已可见的大级别趋势末端
Input:     冻结 20 事件 + FATE 标签。1H 结构状态。无 EMA / OF
```

不准改三买定义。即使 2 个 REENTRY 都在后段，也不改定义。

```
T_3 之前（最后一根已收盘 1H）
  HTF_STATE     RANGE / TRANSITION / TREND_UP / TREND_DOWN
  TREND_AGE_H   当前 TREND_* 已持续小时；非 Trend = 0
  SEGMENT       EARLY <12h | MID 12–48h | LATE ≥48h | SHIFT = RANGE/TRANSITION
  BOX_DIST_ATR  15m 收盘相对 1H 中枢盒子、离开方向上的距离
  N_PRIOR_3RD   T_3 之前同向三买/三卖个数
```

问：2 个 REENTRY 的前置状态是否明显不同于 18 个 RESUME？

n_REENTRY=2 → 只做描述归因，不准宣布 Fate Contrast，不准当 Setup。

---

## 封存语义

不准写成「三买在趋势末端容易失败」。

两个 REENTRY 都在较长的 1H TREND（LATE），但机制不同：逆大级别 vs 同向后段。

**SHIFT ≠ 危险。** T_3 时 RANGE/TRANSITION 的 7 个全部 RESUME。

层级：

```
第三类买卖点     短期延续 PASS（18/20）
Trend Age        候选解释变量。仅 ATTRIBUTION，不是 Filter
EMA52            冻结。可能只是末端回撤路径上的位置
OF               不进
```

全 20 分布见 `DIST.txt`。LATE 只有 3 个事件。样本增大且 Early/Mid 稳定少 REENTRY、Late 稳定多，才有资格升级 Trend Maturity Modifier。在此之前不准把 LATE 写进三买规则。

