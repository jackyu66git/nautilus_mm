# CHAN_SETUP_DEFINITION_001

```
Experiment:     CHAN_SETUP_DEFINITION_001
Type:           Interpretation Layer 第一枪。最小 Setup Candidate 定义。
Status:         CONTRACT FROZEN
                Census AUTHORIZED / 本枪只读 Tape
Replay / MFE / MAE / Entry:  BLOCKED
Input:          CHAN_DESK_REPLAY_001 TAPE-90D only
SMC / OF 作为找点:  FORBIDDEN
```

问：

> 从 State Tape 的每一个已收盘时刻，仅用当时可见信息，机器能否无歧义判断：市场是否进入一个值得进一步观察的结构状态？

不问：买不买、赚不赚、是不是 B1、SMC 成不成立、OF 支不支持。

```
客观 → 因果 → 可重复 → 可统计 → 才谈经济结果
```

禁止：看起来像 Setup → 人工挑 → 再回测。

---

## 对象（1）

**Setup_CANDIDATE** 不是完整交易 Setup。它只回答：这里是否进入观察状态。

机械定义，三件同时成立，缺一不可：

```
1H leftover 空间已存在     htf_anchor_count >= 1
        ∧
15m 已确认分型             ltf_fx ∈ {TOP, BOTTOM} 且 ltf_fx_id 非空
        ∧
该分型身份第一次出现       本行是 Tape 上该 ltf_fx_id 的第一行
        ↓
Setup_CANDIDATE
```

空间对象 = Tape 上的 **leftover** 历史锚点（`T_ZS_COMPLETE < t` 已由 001 保证）。  
**不是** living 当前盒子（问法已关）。  
**不是** `B1_LOCK`（那是更晚的结构真值旗标）。  
**不是** SMC。**不是** OF 阈值。**不是** CONTACT 过滤。

结构事件 = 15m 分型身份 `ltf_fx_id` 的**首次出现**。同一 `ltf_fx_id` 在后续连续 K 上的停留，是持续时间，不是新 Candidate。

`ltf_fx_id` 是引擎身份字符串（可能是 naive 引擎时区），**只作 identity**，不拿它和 UTC 的 `t` 比大小。在线钟只用 Tape 的 `t`。

---

## 在线时钟（2）

```
T_SETUP_VISIBLE = 满足定义的那一行的 t
setup_id        = ltf_fx_id
```

硬门：

```
T_SETUP_VISIBLE 只用已收盘 15m（Tape.t）
T_SETUP_VISIBLE < 任何未来结果钟
T_SETUP_VISIBLE 不得等于或晚于 T_B1 / T_B2 / MFE 窗口
```

因此 Candidate **不能** 用 `b1_lock==true` 当出生条件：那会把 T_SETUP_VISIBLE 钉在 B1 上。

Census 若对照 B1：只允许 `T_SETUP_VISIBLE < t_of_that_b1_lock`。相等或更晚 = 泄漏，丢弃该对照，不改定义。

001 的行字段 `T_FX_VISIBLE` 是**当前 bar 的 close**，不是分型首次可见时刻。本 ID **不准用该字段当 T_SETUP_VISIBLE**。首次可见必须从 `ltf_fx_id` 第一次出现的 `t` 推出。不准回头改 001 Tape。

---

## 绝对不能用（3）

| 禁止 | 原因 |
|------|------|
| 未来 K / 未收盘 K | 泄漏 |
| `b1_lock` / `b1_lock_id` 当出生条件 | 把 B1 当 Setup；破坏 T_SETUP < T_B1 |
| B2、LTF_B2、未来标签 | 真值不是观察状态 |
| living HTF 盒子 / `htf_living` 当必要条件 | 当前盒子问法已关 |
| CONTACT / ABOVE / BELOW 当过滤 | 那是空间库存，不是本对象；不准猎阈值 |
| OF 数值当谓词（delta/HHI/push/speed） | OF 不负责找点 |
| SMC / sweep / MSS / BOS | 尚未客观化；不能偷换成 Setup |
| allow / Entry / Stop / MFE / MAE / WR | 交易层 |
| 改 CHAN_DESK_REPLAY_001 的钟或窗口 | 基准漂移 |
| 另起市场历史 | Input 必须是 001 Tape |

OF / SMC 以后只问：在**已经出生的** Candidate 内部有没有增量。不抢找点。

---

## 去重（4）

```
同一 ltf_fx_id  →  恰好一个 setup_id
```

连续若干根 15m 上 `ltf_fx_id` 不变：只计一次。  
`ltf_fx_id` 变为另一个值：旧 Candidate 结束，新身份若仍满足 leftover≥1 则新出生。

结束时刻（仅普查用，不是交易离场）：

```
T_SETUP_END = 该 setup_id 在 Tape 上最后连续出现的 t
duration    = T_SETUP_END − T_SETUP_VISIBLE
```

不准按时间邻近合并不同 `ltf_fx_id`。不准按价格距离合并。

---

## 本阶段做什么 / 不做什么

**做：** 从 Tape **只读**扫描 Setup_CANDIDATE。报告数量、频率、持续时间、间隔、出生时 leftover 个数、fx 侧。

**不做：** 回测、MFE/MAE、B1→B2、OF、SMC、Entry、任何阈值。不准改 Tape。

```
Fact Tape
   ↓
Setup_CANDIDATE          ← 本 ID 只定义到这里
   ↓
（以后）Setup 自然结果
   ↓
（以后）SMC 是否解释内部差异
   ↓
（以后）OF 是否有增量
```
