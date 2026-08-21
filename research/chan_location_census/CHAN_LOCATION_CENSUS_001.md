# CHAN_LOCATION_CENSUS_001

```
Track:     结构确认时相对中枢的位置普查。独立于 continuation 封存线
Phase:     描述性 Census。不设 ATR 阈值。不是 EMA52
Input:     冻结 47 事件 + 冻结 zg/zd。同一 90 天窗口
```

不是 CHAN_LOCATION_NULL_001 对照实验。不是 EMA52 绕路。

T0 位置（中枢盒子自身尺度，无新阈值）：

```
pos = (close − zd) / (zg − zd)
IN        0 ≤ pos ≤ 1
OUT_HIGH  pos > 1
OUT_LOW   pos < 0
```

不准：0.5/1/2 ATR 分桶、NEAR/FAR、改买卖点、扩窗、EMA、OF、Trend Age。
T+1 = 冻结纯 continuation（27/47）。不准用 29/47 Fate。

Census（冻结）：
n=47 IN=1 OUT=46 OUT_HIGH=28 OUT_LOW=18 T+1=27
B1 18 全 OUT · B2 1 IN / 8 OUT · B3 20 全 OUT
PASS / HOLD_NO_SPLIT。IN n<5。位置与事件定义共线。
封存：Location = 结构定义的伴生属性，不是独立 Location Signal。
不能建立「中枢外 → continuation 更强」。OUT_HIGH/OUT_LOW ≠ Modifier。
不准 ATR 再切 OUT。不准绕开 EMA52。空仓。
