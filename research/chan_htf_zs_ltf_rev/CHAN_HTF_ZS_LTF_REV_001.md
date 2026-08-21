# CHAN_HTF_ZS_LTF_REV_001

```
Setup 线已关闭。本 ID 是新对象，不是把分型 Candidate 优化回来。
问：1H 当前中枢（living）处于 A/B/C 时，下一根 15m 的笔方向是否更常反转？
Y = LTF bi_dir 变化。B1 只做标签。无 OF / SMC / 交易。
```

对象 = 15m 已收盘 K `t`，且当时存在 **living** 1H 笔中枢（`has_next=False` 的最新一个）。  
不是 leftover 历史锚点。不是 15m 新分型。

```
A_INSIDE     15m 高低全在 (zd, zg) 内
B_BOUNDARY   触及 zg 或 zd
C_AWAY       完全在盒子上方或下方（离开/在外）
NONE         当时没有 living 中枢（对照，不是第四个中枢状态）
```

`zg/zd` = 该时刻引擎里该中枢当前值（递归中可变）。15m 高低来自与 Tape 同一份 1m。

```
Y = 下一根 15m 的 ltf_bi_dir ≠ 本根 ltf_bi_dir
    且两边都 ∈ {UP, DOWN}
label_b1 = 下一根 b1_lock
不准把 B1 当 y
```

只报告：各状态 n、反转次数、rev_share。不设阈值、不收成 Setup、不接交易。
