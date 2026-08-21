# CHAN_HTF_HIST_ANCHOR_LTF_B1_001 — Q4

```
Experiment:     CHAN_HTF_HIST_ANCHOR_LTF_B1_001
Phase:          4  FAIL / NO_FATE_CONTRAST
Unit:           B1 event n=5（不是 23 pair / 92 rail）
Replay:         DONE
OF / SMC / MACD / MFE / MAE / Entry / 换 TF:  FORBIDDEN
```

问：历史 HTF 锚点空间关系，是否改变 LTF B1 的后续结构命运（B2 vs no B2）。  
附问：B1 是否更容易发生在历史边界/极值 CONTACT 附近——必须按 `anchor_count_at_B1` 分层。

---

## 单位

Phase 0 的 23 行 collapse 成 5 个 B1。一个 B1 看见 8 个中枢只计一次。

LTF_B2 来自 `CHAN_B1_B2_EARLY_001` 同一批 retrospective overlay。不是实时预测。

---

## 门

| 门 | 结果 |
|----|------|
| C0 | PASS unit=B1 n=5 |
| C1 | PASS B2=5/5 contact_any=3/5 zg=1 zd=2 gg=1 dd=1 |
| C2 | PASS 分层 bar 基线可算。P(contact\|B1)=0.600 vs matched=0.198 |
| C3 | FAIL B2=5 no_B2=0 |

---

## 命运

5/5 B1 都是 B2_TRUTH。没有阴性对照。本样本无法回答 ABOVE / CONTACT / BELOW 是否改变 B1→B2。

不准换周期找 no-B2。

---

## CONTACT 与数量混杂

非 B1 的 15m bar，触及任一历史轨的比例随 leftover 个数上升：

| leftover n | n_B1 | B1 CONTACT | n_bars | bar CONTACT 率 |
|------------|------|------------|--------|----------------|
| 0 | 0 | — | 518 | 0% |
| 1 | 1 | 否 | 431 | 0% |
| 2 | 0 | — | 624 | 13.6% |
| 3 | 1 | 是 | 719 | 18.8% |
| 4 | 1 | 是 | 1135 | 21.2% |
| 5 | 0 | — | 712 | 30.6% |
| 6 | 0 | — | 672 | 25.0% |
| 7 | 1 | 是 | 323 | 25.7% |
| 8 | 1 | 否 | 622 | 33.3% |

bar 率从 0% 升到 33%。后期更容易碰到某个历史锚点，是因为历史中枢更多。这正是必须记录 `anchor_count_at_B1` 的原因。

B1 CONTACT=3/5，分层期望之和 ≈ 0.99。描述性偏高，但：

- n=5
- leftover 最多的 B1（n=8）没有 CONTACT
- 最近完成 leftover 自身 CONTACT 只有 1/5

所以：**没有成立**「历史 HTF 中枢携带了超出数量增加本身的 B1 结构信息」。

四条轨分开看已经很稀（1 / 2 / 1 / 1）。不准组合。

---

## 不准继续的

- 把 0.600 vs 0.198 写成 Edge
- 组合 zg/zd/gg/dd
- 接 OF / SMC / MACD
- 上 MFE / MAE / 收益
- 换 TF 找命运对照
