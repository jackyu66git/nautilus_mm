# CHAN_SETUP_STRATA_001

```
Experiment:     CHAN_SETUP_STRATA_001
Type:           Interpretation Layer。Setup_CANDIDATE 出生时刻的客观状态分层。
Status:         CONTRACT FROZEN
                Replay PASS / STRATA_OK
                结论 NO_STATE_CONTRAST。此 ID 关闭
                数字不可变。不准四维交叉。不准收紧 Setup
不准收紧 Setup / 不准改 Outcome:  LOCKED
Input:          CHAN_DESK_REPLAY_001 Tape
                + CHAN_SETUP_DEFINITION_001 CENSUS_EVENTS（2342，不可变）
                + CHAN_SETUP_OUTCOME_001 OUTCOME_EVENTS（2341，不可变）
Y:              已冻的 outcome_class。不准改 Outcome 定义。
SMC / OF / 收益 / B1:  FORBIDDEN
参数优化 / 收紧 Setup:  FORBIDDEN
```

问：

> 在 Setup 出生那一刻已经可见的客观状态，会不会对应不同的自然 Outcome 分布？

不问：怎么过滤更赚钱、哪个 leftover 阈值更好、要不要改成交易 Setup、B1 在哪一层更密。

```
Setup_CANDIDATE     已冻。条件宽，86% DISSOLVES 是观察态寿命短的结果，不是 Edge 判决
        ↓
Natural Outcome     已冻。CONTINUES=0 REVERSES=321 DISSOLVES=2020
        ↓
客观状态分层        ← 本 ID
        ↓
（以后，仅当表格显示结构差）才允许新 ID 定义更严 Setup
```

本枪**不是** Outcome 第二轮，也**不是** Setup 优化。  
2342 仍是高频观察态母集。Interpretation Layer 仍未形成交易 Setup。

---

## 对象

每一行 = 一个已有 Outcome 的 `setup_id`。

```
宇宙            = OUTCOME_EVENTS 2341 条
CLOCK drop      = 1 条，单列，不进入分层表
不准从 2342 再删
不准按 Outcome 回删 Setup
```

X 只来自出生行（`tape_row` / `T_SETUP_VISIBLE`）当时 Tape 字段。  
Y 只来自已冻 `outcome_class`。  
不准用 `T_OUTCOME_VISIBLE` 之后的任何字段定义层。

---

## 四条单维分层（预先钉死）

只做 **4 张单维列联表**。不准做 4 维笛卡尔积。不准事后加交互项。不准把 leftover=1..10 收成「少/多」。

### 1. HTF anchor 数量

```
anchor_n = 出生行 htf_anchor_count
水平     = 整数 1,2,… 原样
```

不准 1–3 vs 8–10。不准因为 Census 里 6 最多就专看 6。

### 2. HTF anchor 空间关系

对象 = 出生行 `htf_leftover` 里 `T_ZS_COMPLETE` 最大的那一个（最近完成的历史中枢）。  
只用它的 **zg / zd**（中枢区间）。**不准**把 zg/zd/gg/dd 四条轨合成一个分数，也不准四轨同时过滤。

```
space_rel(latest):
  side_zg 或 side_zd == CONTACT     → CONTACT_BOX
  两者都是 ABOVE                    → ABOVE_BOX
  两者都是 BELOW                    → BELOW_BOX
  其余                              → STRADDLE_BOX
```

`gg` / `dd` 本枪不读。living 盒子不读。

### 3. 15m 笔状态

出生行：

```
bi_state:
  ltf_bi_dir 非 UP|DOWN             → BI_DIR_NONE
  ltf_bi_sure == True               → UP_SURE / DOWN_SURE
  否则                              → UP_UNSURE / DOWN_UNSURE
```

不准把 sure/unsure 合并。不准按笔长度或 MACD 再切。

### 4. 分型方向

```
fx_side = 出生行 ltf_fx ∈ {TOP, BOTTOM}
```

就是 Census 已有的 1171 / 1171 切面，本枪只问它与 Outcome 是否同分布。

---

## 只报告什么

每张表每个水平：

```
n
CONTINUES / REVERSES / DISSOLVES / NEXT_EVENT / CENSOR 的计数
```

可以附一列 DISSOLVES 占比，**只描述分布**，不叫命中率，不设「差多少算有结构含义」的阈值。

本 ID 的 Replay 结论只允许：

```
PASS / STRATA_OK     四张表按合同产出
FAIL / CLOCK 或母集漂移
```

**不准**输出 NEW_SETUP。  
**不准**因为某格 REVERSES 更高就当场收紧 Candidate。收紧必须新 ID。

---

## 绝对不能用

| 禁止 | 原因 |
|------|------|
| 改 Setup 定义 / 改 Outcome 词汇 | 基准漂移 |
| leftover 二分化、距离%、NEAR | 参数优化 |
| 四轨组合、CONTACT 当过滤 | 已关的猎轨 |
| 4 维交叉、事后交互 | 空格子猎结果 |
| `label_b1` 当层或当 y | 现在不研究 B1；n=5 会伪装成质量 |
| OF / SMC / MFE / MAE / WR / Entry | 尚未轮到；不是本问 |
| p 值 / 显著性作为收紧闸门 | 把分层变成选参 |
| 1m 重放、另起历史 | 必须同一条 Fact Tape |

---

## 时钟

```
X 的钟 = T_SETUP_VISIBLE（出生行）
Y 的钟 = 已冻 T_OUTCOME_VISIBLE
硬门   X 不用未来；Y 不反向定义 X
```

不准用 `T_FX_VISIBLE` 字段。

---

## 本阶段

**做：** 只读 Tape + 已冻 Census + 已冻 Outcome，产出四张单维表。

**不做：** 收紧 Setup、改 Outcome、开 SMC、研究 B1、回测。

```
Fact Tape
   ↓
Setup_CANDIDATE          已冻 2342。仍不是交易 Setup
   ↓
Natural Outcome          已冻
   ↓
客观状态分层              ← 本 ID 合同
   ↓
（以后）是否定义更严 Setup
   ↓
（以后）SMC / OF
```
