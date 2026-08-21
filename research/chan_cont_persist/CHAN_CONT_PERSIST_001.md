# CHAN_CONT_PERSIST_001

```
Track:     Structure Increment 是瞬时还是持续。B1/B2/B3 HOLD 只读
Phase:     固定 H=1,2,3,4。结构与 Null 同一 continuation 定义
Input:     同一 90 天窗口。冻结 47 事件。不准优化 H
```

链（买；卖对偶）：

```
C(H): 对 k=1..H，high[i+k] > high[i+k-1]
H2 包含 H1。不是「第 H 根仍高于 T0」。
```

Null = 非确认 15m K，同一条链。混合对照 = (n_buy×p_up(H)+n_sell×p_down(H))/n
Y 只用纯 continuation。不用 29/47 Fate。

Census（冻结）：
H1 27/47=0.574 vs 0.463  delta=+0.111  复现 CONT_NULL
H2  8/47=0.170 vs 0.232  delta=−0.062
H3  3/47=0.064 vs 0.113  delta=−0.049
H4  1/47=0.021 vs 0.056  delta=−0.034
PASS / ONE_BAR_ARTIFACT。H1 必须=27/47。
B1 H2=4/18 · B2 H2=2/9 · B3 H2=2/20。H2 起无正增量。
CLOSED / ONE_BAR_ARTIFACT。线封存。数字不可变。
负 delta ≠ 反向 Alpha。不准解释 −6.2pp。
不改 H2，不换成相对 T0，不重做 Null，不扩窗，不改买卖点，不合桶。
不因本线开 Lifecycle / EMA52 / OF。
