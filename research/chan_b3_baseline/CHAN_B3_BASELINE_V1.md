# CHAN_B3_BASELINE_V1

```
Track:     Structure-only Trading Contract。不是 Census。不是优化
Phase:     最小可执行三买/三卖 baseline。看合同长什么样
Input:     冻结 20 个 15m B3/S3（CHAN_3RD_POINT_001）。同一 90 天窗口
```

不是为了证明赚钱。跑完才知道问题在 Entry / Stop / Target / 方向。

## 冻结合同

| 槽 | v1 |
|----|----|
| Signal | 仅 15m B3 / S3。分记。不合桶当 Alpha |
| Entry | T0 确认收盘后，下一根 15m **开盘** |
| Stop | B3 = zd；S3 = zg。无 ATR buffer |
| TP | 1R。B3：TP = Entry + (Entry−zd)；S3 对偶 |
| Time | 24h = 96 根 15m。标记 TIME_EXIT，不混进 Win/Loss |
| Size | 每笔风险 = 权益 0.5%。Account=100000 → 500 USDT |
| 成本 | 无手续费、滑点、资金费。不是 Economic PASS |

不准：EMA52、Trend Age、OF、ATR、改 zg/zd、扩窗、合 B1/B2、优化 TP/Stop。

## 成交与路径

```
T0 确认收盘
     ↓
T1 open = Entry
     ↓
同根及之后 15m OHLC
     ↓
同根既触 TP 又触 Stop → LOSS（保守，无 1m 路径）
TP first → WIN = +1R
Stop first → LOSS = −1R
24h 都没有 → TIME_EXIT（按当时 close 计 R）
样本结束仍未满 24h → CENSOR
Entry 已穿过 Stop（R≤0）→ SKIP
```

`hours_*`：从 T1 open 起，0 = 入场 K 内触发。不是持仓研究。

MFE/MAE 到实际离场（R 单位）。另报 `mfe_24h`：入场后 24h 内最有利，用来看 1R 是否太近。不是第二套策略。

事件独立结算，不是组合。重叠持仓不合并。

## 输出

n、WIN、LOSS、TIME_EXIT、SKIP、CENSOR、Avg R、Median R、MFE、MAE、mfe_24h、
Median time to TP/Stop、B3 vs S3。

`BASELINE_OK` ≠ 有 Edge ≠ 可上实盘。

## 冻结结果

`PASS / BASELINE_OK`。hint=`TIME_DOMINATED`（观察标签，不是下一枪）。

n=20 全成交。SKIP=0。CENSOR=0。same_bar_both=0。无费。Account=100000，每笔风险 500。

| | n | WIN | LOSS | TIME | wr(已决) | avg R | med R | sum R | PF | mfe p50 | mae p50 | mfe24 p50 |
|--|--|--|--|--|--|--|--|--|--|--|--|--|
| ALL | 20 | 4 | 4 | 12 | 0.50 | −0.029 | 0.124 | −0.58 | 1.00 | 0.52 | 0.46 | 0.54 |
| B3 | 12 | 2 | 2 | 8 | 0.50 | −0.026 | 0.125 | −0.31 | 1.00 | 0.54 | 0.49 | 0.54 |
| S3 | 8 | 2 | 2 | 4 | 0.50 | −0.034 | 0.124 | −0.27 | 1.00 | 0.36 | 0.42 | 0.40 |

hours_to_tp p50=1.25h（n=4）。hours_to_stop p50=4.25h（n=4）。TIME 标记 23.75h = 第 96 根起点，收盘满 24h。
1R 宽度 p50=1325。mfe_24h ≥1R 的 6/20，≥2R 的 3/20。

不是 A（TP 太近）：24h 中位有利只有 0.54R。
不是 B（Stop 太紧）：只有 4/20 先碰到 Stop。
不是 D/E：B3/S3、多空都接近。
主形态：24h 内多数走不到 1R，超时离场。不准本枪改 Time / TP / Stop。
不等于「Entry 没 edge」已证伪，也不等于可拉长 Time。下一问另授权。

## 禁止

止损优化、改 1R、改 24h、EMA、OF、Trend Age、ATR、手续费曲线拟合、合 B1/B2、把 BASELINE_OK 当 Edge。

