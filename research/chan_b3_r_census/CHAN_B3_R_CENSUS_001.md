# CHAN_B3_R_CENSUS_001

```
Track:     Raw R 分布。插在 G0 之前
Phase:     描述性 Census。不是优化。不改策略
Input:     冻结 V1 20 笔 TRADES.jsonl
Repo:      https://github.com/jackyu66git/nautilus_mm
```

只问：结构 Stop 产生的 Raw R，是不是有严重长尾。
结构有效 ≠ 交易距离有效。

不改：Entry、Stop、TP、Time、买卖点定义。不要 Cap Stop。不定 5%/10%/15%。

```
Raw R_px   = |Entry - Stop|
R_pct      = Raw R_px / Entry
tp_0.5_pct = 0.5 * R_pct
```

## 预注册形状闸

```
LONG_TAIL  若  p90/p50 ≥ 2.5  或  p95/p50 ≥ 3.0  或  max/p50 ≥ 5.0
NO_TAIL    否则
```

NO_TAIL → 恢复 G0 WAIT。
LONG_TAIL → G0b：`R_pct > 本枪 p90` → NO TRADE。Stop 仍是盒沿。

接回见 `research/CHAN_TO_LIVE.md`。

## 冻结结果

`NO_TAIL / SHAPE_OK`。n=20。G0b = N/A。next = G0 WAIT。

R_pct = |Entry − Stop| / Entry：

| | p25 | p50 | p75 | p90 | p95 | max |
|--|-----|-----|-----|-----|-----|-----|
| all | 1.36% | 2.12% | 2.40% | 4.04% | 4.38% | 6.19% |
| B3 | 0.96% | 1.54% | 2.22% | 2.34% | 2.40% | 4.38% |
| S3 | 1.38% | 2.35% | 3.79% | 4.04% | 4.04% | 6.19% |

形状闸：p90/p50=1.91、p95/p50=2.07、max/p50=2.92。阈值 2.5 / 3.0 / 5.0。未触发。
最大一笔 S3 R_pct=6.19%，TIME_EXIT，mfe=0.63R。不是 12%–31% 那种长尾。
0.5R 价格距离 p50≈1.06%、max≈3.09%。不改 Stop。不定 5/10/15%。不跑 Recheck。
