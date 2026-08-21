# CHAN_HTF_HIST_ANCHOR_LTF_B1_001 — Phase 0

```
Experiment:     CHAN_HTF_HIST_ANCHOR_LTF_B1_001
Phase:          0  PASS / HIST_ANCHOR_EXISTS
                4  FAIL / NO_FATE_CONTRAST
Decision:       历史 leftover 锚点成立。Q4 无 B2 命运对照
Replay:         Phase 0 DONE。Q4 DONE
OF / SMC / MACD / Entry / MFE / MAE:  FORBIDDEN
HTF B1/B2:      FORBIDDEN
```

合同数字见 SMOKE 段。本文件钉定义。

---

## 与上一枪的分工

| ID | 对象 | 状态 |
|----|------|------|
| CHAN_HTF_ZS_LTF_B1_001 | **living** 当前盒子 × 当时 LTF B1 | Phase 0 数字不可变。问法关闭 |
| 本 ID | **leftover** 历史中枢的 zg/zd/gg/dd × 未来 LTF B1 | 定义已冻。未跑 |

living 盒子可以提前存在，仍不是递归空间记忆。  
历史锚点必须：后继中枢已出生，扩员已停，钟严格早于 B1。

---

## Q1 身份

`T_ZG = T_ZD = T_HTF_ZS_VISIBLE`  
`T_GG = T_DD = T_ZS_COMPLETE`（第一根 HTF 收盘，该 zs 已有 next）  
硬门：被使用的轨 `T_ANCHOR < T_LTF_B1`

gg/dd 在完成前会随 `ZS_EXPAND` 移动，出生时刻不能当 gg/dd 锚点。

---

## Q2 稳定

zg/zd：相对出生未改写。  
gg/dd：相对完成时刻未改写。  
四条轨独立。gg 动不等于 zg 无效。

---

## Q3 空间

`leave.end_klc` 的 `[low, high]` 对每条轨：

`ABOVE` / `CONTACT` / `BELOW`

CONTACT = 触及。不准百分比。多个历史中枢全部记账，不准挑主中枢。  
SMOKE-60D：92 轨里 CONTACT=5，ABOVE=46，BELOW=41。改写=0。

---

## Q4

已跑。单位 = B1 event。

```
Q4 = FAIL / NO_FATE_CONTRAST
C0 PASS unit=B1 n=5
C1 PASS B2=5/5 contact_any=3/5
C2 PASS P(contact|B1)=0.600 vs count-matched bar=0.198
C3 FAIL 没有 no-B2
```

5/5 都是 B2，命运对照不存在。不准换 TF。

CONTACT 描述性高于分层 bar 基线，但 n=5，且 leftover 最多的 B1 没有 CONTACT。不成立「超出数量增加的结构信息」。不准组合四轨。不准接微观层 / 收益。

---

## Forbidden

- 换 TF 找 no-B2
- living 末中枢当历史锚点
- pair 复制 / 组合 zg zd gg dd
- OF、SMC、MACD、Entry、MFE、MAE
- ledger `HTF_B1` / `HTF_B2` / `HTF_BSP`
