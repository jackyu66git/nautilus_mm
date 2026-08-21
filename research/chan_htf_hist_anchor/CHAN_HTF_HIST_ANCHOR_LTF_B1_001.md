# CHAN_HTF_HIST_ANCHOR_LTF_B1_001

```
Experiment:     CHAN_HTF_HIST_ANCHOR_LTF_B1_001
Status:         Phase 0 = PASS / HIST_ANCHOR_EXISTS
                Q4 = FAIL / NO_FATE_CONTRAST
Phase:          0  PASS / HIST_ANCHOR_EXISTS
                4  FAIL / NO_FATE_CONTRAST
Replay:         Phase 0 DONE。Q4 DONE。不准换 TF / 接微观层 / 做收益
Type:           历史 HTF 结构锚点 × 未来 LTF B1
                不是当前中枢盒子。不是 HTF B1。不是共振预测
Engine:         user_data/Chan
HTF object:     已完成（leftover）笔中枢的 zg / zd / gg / dd
LTF object:     B1_LOCK。Q4 读 retrospective LTF_B2。不准完成率 / WR / PF
Predecessor:    CHAN_HTF_ZS_LTF_B1_001  Phase 0 数字不可变
                该 ID 问的是「当前 living 盒子」。时钟太静态，本 ID 不继承其结论
Why opened:     小级别 B1 往往先发生；大级别中枢是递归之后才完成的。
                有因果意义的是：已完成 HTF 结构的边界，成为未来 LTF 转折的空间记忆
OF / SMC / MACD / Entry / HTF BSP:  FORBIDDEN
Success / WR / PF: FORBIDDEN
```

问：

> 历史高级别结构的 zg / zd / gg / dd，在 LTF B1 之前是否已经作为稳定锚点存在？
> B1 与这些锚点是什么空间关系？

不问：当前 1H 中枢里面有没有 15m B1。不问 HTF 能不能预测 LTF。Q4 只问结构命运，不问赚钱。

---

## 为什么不是 CHAN_HTF_ZS_LTF_B1_001

上一枪把 **living** HTF 中枢当成当前空间盒子去套当时的 LTF B1。

```
当前 HTF ZS          ← 错。这是正在形成的盒子
      ↓
当前 LTF B1
```

Phase 0 已证明：盒子可以提前存在，但 5/5 B1 都在盒子 **OUTSIDE**。  
那不是「HTF 中枢无效」，是问错了对象。LTF 结构往往先走完，HTF 中枢随后才递归完成。

本 ID 的时钟：

```
过去已经完成的 HTF 中枢
        │
        ├── zg    上沿（出生即冻）
        ├── zd    下沿（出生即冻）
        ├── gg    完成后的历史高点
        └── dd    完成后的历史低点
              │
              │  历史结构空间 / 空间记忆
              ▼
        后续 LTF 走势
              │
              ▼
          LTF B1
              │
              ▼
          LTF B2     ← Q4 才问。现在 FORBIDDEN
```

递归优势不是「大周期预测小周期」，而是：

```
        LTF B1
          │
          ▼
      LTF 结构
          │
          ▼
     HTF 中枢递归形成并完成
          │
     ┌────┴────┐
     ZG  ZD  GG  DD     ← 冻成历史锚点
     └────┬────┘
          │
          ▼
     未来 LTF B1
```

---

## 对象锁

一个 HTF 中枢要成为 **历史锚点**，在 `T_LTF_B1` 必须同时成立：

1. 已是 leftover：当时 `zs.next` 存在（不再是末中枢，不再 `ZS_EXPAND`）
2. `T_ZS_COMPLETE < T_LTF_B1`（完成时刻严格早于 B1）
3. 身份键仍是 `zs.start_bi.start_time`
4. zg / zd 相对出生未改写
5. gg / dd 相对 **完成时刻** 未改写

living 末中枢 **不是** 本对象。那是上一枪的当前盒子。

引擎事实（只引用，不重判 Opportunity）：

| 轨 | 何时第一次可知 | 之后会不会动 |
|----|----------------|--------------|
| zg / zd | 出生：连续三笔 `is_sure`，`get_zs_range` | 扩员 **不重算**。OWN_CHAN_ZS 已冻 |
| gg / dd | `set_zs_bi_list` 随成员更新 | **living 期间会随 ZS_EXPAND 移动** |
| 完成 | 后继中枢出生，`set_next` | leftover 后扩员停止，gg/dd 才有资格冻 |

所以四条轨的在线时刻 **不是同一个钟**：

| 时刻 | 定义 |
|------|------|
| `T_ZG` = `T_ZD` | `T_HTF_ZS_VISIBLE`：前缀第一次发出该 zs |
| `T_ZS_COMPLETE` | 第一根已收盘 HTF bar，该 zs 已有 `next` |
| `T_GG` = `T_DD` | `T_ZS_COMPLETE`。完成前 gg/dd 不准当锚点 |
| `T_LTF_B1` | 第一次 LTF `B1_LOCK` 的闭合 15m（与上一枪相同） |

硬门：每条被使用的轨都满足 `T_ANCHOR < T_LTF_B1`。相等或更晚 → 不是这笔 B1 的历史锚点。

HTF 只用：

```
klu → klc → cal_bi_list → cal_bi_zs_list_pure
```

禁止 `find_all_bsp` / `find_first_bsp` / 线段中枢 / HTF B1 / HTF B2。  
LTF 标签字段必须带 `LTF_` 前缀。

因果：`T_LTF_B1` 时刻只用 `HTF.close < T_LTF_B1`。未收盘 HTF 不得进前缀。

---

## 多个历史中枢

不准事后挑「好看的」中枢，也不准再用 `pos` 离 `[0,1]` 最近当主中枢——那是当前盒子的规则。

Phase 0 对 **每一个** 合格历史中枢记账。B1 可以同时看见 0、1、多个历史锚点。  
`NO_HIST_ANCHOR` = 当时一个合格 leftover 都没有。

---

## Q1 身份（Phase 0）

每个 zg / zd / gg / dd 第一次在线可知的时间。必须 `T_ANCHOR < T_LTF_B1`。

报告：有多少 LTF B1 至少看见一个合格历史中枢；每个 B1 看见几条轨。

大量 `NO_HIST_ANCHOR` → 历史锚点没有实时意义 → 关闭本 ID。

---

## Q2 稳定性（Phase 0）

在 `T_ANCHOR → T_LTF_B1`：

| 轨 | 改写则 |
|----|--------|
| zg | 该中枢不能当历史锚点 |
| zd | 同上 |
| gg | 若完成后再动，gg 不能当锚点；zd/zg 仍可分开记 |
| dd | 同 gg |

四条轨独立资格。不准因为 gg 会动就宣布整个中枢不存在。  
末中枢 `is_sure` 闪烁不是改写，不进身份。

---

## Q3 空间关系（Phase 0）

不准距离百分比。不准「附近」阈值。

价格锚：LTF B1 的 `leave.end_klc` 的 `[low, high]`（与上一枪同一根 K）。

对每一条合格轨 `level`：

| 桶 | 几何 |
|----|------|
| `ABOVE` | `low > level` |
| `CONTACT` | `low <= level <= high` |
| `BELOW` | `high < level` |

ZG / ZD / GG / DD 各记一列。CONTACT 就是本阶段的「附近」。不要再造百分比。

---

## Q4 结构结果（已授权，克制）

只问：历史 HTF 锚点的空间关系，是否改变 LTF B1 的后续结构命运（B2 vs no B2）。

```
历史 HTF Anchor
       │
       ├── ABOVE
       ├── CONTACT
       └── BELOW
             │
             ▼
          LTF B1          ← 实验单位。不是 anchor×B1 pair
             │
        ┌────┴────┐
        │         │
       B2        no B2
```

不问赚钱。暂时不问 MFE/MAE。不接 OF / SMC / MACD。不换周期。

硬约束：

1. 单位是 **B1 event**。23 行 / 92 轨不得当 23/92 个样本。一个 B1 看见 8 个中枢不能复制 8 次。
2. 四条轨分开记。不准组合成复杂特征。最先问：B1 是否更容易发生在历史边界/极值 CONTACT 附近。
3. 必须记录 `anchor_count_at_B1`。后期 B1 天然看见更多中枢；不控这个会得到假的「后期更容易共振」。
4. 第一目标不是 Edge，而是：历史中枢是否携带了超出「锚点数量增加」本身的 B1 结构信息。

对照：

| 列 | 含义 |
|----|------|
| B1 | LTF B1_LOCK 事件 |
| `anchor_count_at_B1` | 当时合格 leftover 个数 |
| `contact_any` | 任一条历史轨 CONTACT |
| zg/zd/gg/dd `_contact_any` | 分轨，不组合 |
| 最近完成 leftover 的四侧 | 预指定对象 = max `T_ZS_COMPLETE`。不是按距离挑 |
| LTF_B2 | EARLY 同一批的 retrospective overlay |

count-matched 基线：非 B1 的 15m bar，按当时 leftover 个数分层，比 `P(contact|B1, n=k)` vs `P(contact|非B1 bar, n=k)`。

本样本 5/5 都是 B2 → `NO_FATE_CONTRAST`。不准换 TF 找阴性。

CONTACT vs count-matched：3/5 vs 分层 bar 基线均值 0.198。描述性更高，但 n=5，且 leftover 最多的那个 B1（n=8）没有 CONTACT。不能写成「超出数量混杂的结构信息已成立」。不准把 zg/zd/gg/dd 组合起来。

---

## 默认只读组合（未授权 replay）

```
symbol:   BTCUSDT-PERP
HTF:      1H  因果闭合
LTF:      15m 因果闭合
data:     nautilus_mm/data/chan_2buy_of/BTCUSDT-PERP/1m.parquet
```

不换周期救。结构关系若不成立：CLOSED。

---

## Forbidden

- 把 living 末中枢当成历史锚点
- 用 HTF B1 当 LTF Context
- 用 `pos` 挑主中枢
- 距离百分比 / 「附近」阈值
- 把 92 轨 / 23 行当独立样本
- zg/zd/gg/dd 组合成复杂特征 / combo_score
- 不记录 `anchor_count_at_B1` 就谈共振
- Q4 完成率 / WR / PF / Entry / MFE / MAE
- OF / SMC / MACD 独立层
- 改 `cal_bi_zs_list_pure` 来通过硬门
- ledger 出现 `HTF_B1` / `HTF_B2` / `HTF_BSP`

```
CHAN_HTF_HIST_ANCHOR_LTF_B1_001 / Phase 0 = PASS / HIST_ANCHOR_EXISTS
Q4 = FAIL / NO_FATE_CONTRAST
不准 OF / SMC / MACD / Entry / living 盒子 / pair 复制 / 换 TF
```

---

## SMOKE-60D-1H-15M Phase 0

Log: `logs/chan_htf_hist_anchor/CHAN_HTF_HIST_ANCHOR_LTF_B1_001/SMOKE-60D-1H-15M/`

LTF B1_LOCK 复用上一枪同一批 5 个事件。HTF 只读 leftover。living 末中枢不是对象。未比较 B1→B2。

| 门 | 结果 |
|----|------|
| C0 | PASS n_LTF_B1=5，历史中枢行 23 |
| C1 | PASS 全部 `T_ZS_COMPLETE < T_LTF_B1`；无 HTF BSP |
| C2 | PASS 5/5 看见至少 1 个历史中枢；NO_HIST_ANCHOR=0 |
| C3 | PASS 92 条轨均可分桶；zg/zd/gg/dd 改写=0 |

每个 B1 看见的历史中枢数随时间增加：1 → 3 → 4 → 7 → 8。这是递归记忆在堆积，不是当前盒子。

| 轨 | ABOVE | CONTACT | BELOW |
|----|-------|---------|-------|
| zg | 10 | 1 | 12 |
| zd | 13 | 2 | 8 |
| gg | 3 | 1 | 19 |
| dd | 20 | 1 | 2 |

CONTACT 共 5 次（92 条轨里）。存在触及，不是距离百分比。不准把 CONTACT 写成 edge。

准确说法：已完成 1H 中枢的 zg/zd/gg/dd **可以**在未来 15m B1 之前作为稳定历史锚点存在。四条轨完成后不再改写。B1 与这些锚点主要是 ABOVE/BELOW，少数 CONTACT。≠ 已证明改变 B1→B2。

---

## SMOKE-60D-1H-15M Q4

单位：5 个 B1 event（从 23 对 collapse，不是 23/92 样本）。LTF_B2 = EARLY retrospective overlay。

| 门 | 结果 |
|----|------|
| C0 | PASS unit=B1 n=5（not pair） |
| C1 | PASS LTF_B2=5/5 contact_any=3/5 zg=1 zd=2 gg=1 dd=1 counts=1,3,4,7,8 |
| C2 | PASS P(contact\|B1)=0.600；count-matched bar 基线=0.198 |
| C3 | FAIL B2=5 no_B2=0 |

| B1 | leftover | contact_any | zg zd gg dd | 最近完成 leftover | B2 |
|----|----------|-------------|-------------|------------------|----|
| 2026-06-25 | 1 | 否 | 0000 | BELOW/BELOW/BELOW/BELOW | 是 |
| 2026-07-13 | 3 | 是 | 1101 | ABOVE/ABOVE/BELOW/ABOVE | 是 |
| 2026-07-23 | 4 | 是 | 0010 | ABOVE/ABOVE/CONTACT/ABOVE | 是 |
| 2026-08-11 | 7 | 是 | 0100 | ABOVE/ABOVE/BELOW/ABOVE | 是 |
| 2026-08-13 | 8 | 否 | 0000 | BELOW/BELOW/BELOW/BELOW | 是 |

非 B1 的 15m bar CONTACT 率随 leftover 个数上升：n=1 → 0%；n=8 → 33%。这就是必须控 `anchor_count_at_B1` 的原因。B1 CONTACT 并不随 leftover 增多而增多：n=8 那个 B1 没有 CONTACT。

期望接触次数（把每条 B1 的分层 bar 率加总）≈ 0.99，观测 3。n=5，描述性偏高，不能写成超出数量混杂的结构信息。四轨不要组合。

```
Q4 = FAIL / NO_FATE_CONTRAST
本样本没有 B2 阴性对照。不准换 TF。不准接 OF / SMC / MACD / MFE / MAE。
历史锚点作为空间记忆仍然成立（Phase 0）。它有没有改变 B1 结构命运：本样本无法回答。
```

