# CHAN_CONT_NULL_001

```
Track:     continuation 是否结构独有。B1/B2/B3 HOLD，只读
Phase:     非结构对照 = 普通 15m K，不是另一种结构信号
Input:     同一 90 天窗口。冻结 Fate 事件时间戳
```

对照对象（冻结）：

```
非事件 15m K = 不是 B1/B2/B3 确认 K 的普通 bar
不准：局部突破 / 分型 / 笔端 / N 根新高 / 离开笔
那些会偷偷变成另一个结构信号。
```

Y = 弱 RESUME 谓词本身（无 REVERSE/REENTRY 赛跑）：

```
买向：下一根 high > 本根 high
卖向：下一根 low  < 本根 low
```

事件侧：按 B/S 方向用同一谓词。
对照侧：全体非事件 K 的 p_up / p_down。
混合对照 = (n_buy × p_up + n_sell × p_down) / n_event

`delta = 事件下一根扩展率 − 混合对照`

Census（冻结）= 后续研究的 Null Baseline 锚点：
合样本 27/47=0.574 vs mix_null=0.463，delta=+0.111 → PASS / STRUCTURE_INCREMENT
B1/S1 12/18=0.667 主贡献 · B2/S2 5/9=0.556 薄 · B3/S3 10/20=0.500≈普通K
null n=8600 p_up=0.454 p_down=0.473
11pp ≠ Alpha。不准三类合桶。不准说三买有 continuation edge。
以后比较只用 27/47 纯 continuation，不用 29/47 Fate（含 2 REVERSE）。

不准改对照为局部突破。不准叠 EMA/OF。B1/B2/B3 HOLD。等待自然样本。
第一复检：各自相对 Null 是否稳定。不是 EMA52。
