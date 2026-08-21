# CHAN_SETUP_OUTCOME_001

```
Experiment:     CHAN_SETUP_OUTCOME_001
Type:           Interpretation Layer。Setup_CANDIDATE 的自然结构结局。
Status:         CONTRACT FROZEN
                Replay PASS / OUTCOME_OK
                数字不可变。不准改分类
MFE / MAE / Entry / OF / SMC:  BLOCKED
Input:          CHAN_DESK_REPLAY_001 Tape
                + CHAN_SETUP_DEFINITION_001 CENSUS_EVENTS（2342，不可变）
SMC / OF / 收益:  FORBIDDEN
leftover 个数分层: FORBIDDEN（本枪不研究）
```

问：

> 一个已经出生的 Setup_CANDIDATE，之后下一次客观结构事件是什么？

不问：赚不赚、该不该买、B1/B2 算不算成功、SMC 能不能解释、OF 有没有增量。

```
Setup_CANDIDATE          市场何时值得观察（已冻，2342 / 90D）
        ↓
Natural Outcome          被观察以后市场自然发生了什么  ← 本 ID
        ↓
（以后）质量是否分层
        ↓
（以后）SMC / OF 是否解释分层
```

2342 是事件母集，不是 2342 个交易机会。本枪不把它升级成交易 Setup。

---

## 对象

母集 = `CHAN_SETUP_DEFINITION_001` 的每一个 `setup_id`。不准增删、不准按 leftover / CONTACT / OF 再过滤。

对每个 `setup_id`，在出生行读取当时可见快照（不是结局）：

```
S0.t            = T_SETUP_VISIBLE
S0.fx           = 出生行 ltf_fx
S0.fx_id        = setup_id
S0.bi_dir       = 出生行 ltf_bi_dir
S0.bi_sure      = 出生行 ltf_bi_sure
```

然后只向前看 Tape 上行序 **严格晚于** 出生行的行，寻找**第一次**成立的结构事件。那一次事件 = 本 Setup 的唯一 Natural Outcome。

---

## 1. 时钟

```
T_SETUP_VISIBLE     已冻。出生行的 t。不准改。
T_OUTCOME_VISIBLE   第一次结构事件所在行的 t
硬门                T_SETUP_VISIBLE  <  T_OUTCOME_VISIBLE
```

扫描起点 = 出生行的下一行（`tape_row + 1`）。出生行本身不是结局。

不准用 Tape 字段 `T_FX_VISIBLE` 当任何钟。  
不准用引擎对象创建时间反推。  
不准用未收盘 K。  
不准把结局钟钉在「最终 B1/B2 成立时刻」上再回头分类。

若一直扫到 Tape 最后一行仍无事件：

```
outcome_event       = CENSOR
T_OUTCOME_VISIBLE   = 最后一行 t
仍须 T_SETUP_VISIBLE < T_OUTCOME_VISIBLE
否则该条丢弃并记 CLOCK，不改定义
```

`T_SETUP_END` / `duration_*` 是 DEFINITION Census 已冻的观察态寿命，本枪可抄作上下文，**不是** Outcome，也不是成败。

价格 excursion / MFE / MAE **本 ID 不做**。Fact Tape 行上没有 OHLC；去 1m 重放价格 = 另起市场历史。留给以后的 ID。

---

## 2. 允许读的未来数据

只读 CHAN_DESK_REPLAY_001 已存在字段，且只读 `t > T_SETUP_VISIBLE` 的行：

| 允许 | 用途 |
|------|------|
| `t` | Outcome 钟 |
| `ltf_fx` / `ltf_fx_id` | 分型身份是否变 |
| `ltf_bi_dir` / `ltf_bi_sure` | 笔方向 / 笔是否确认 |
| `b1_lock` / `b1_lock_id` | **标签**，不参加抢第一事件 |

禁止读（即使 Tape 上有）：

| 禁止 | 原因 |
|------|------|
| 一切 OF 字段 | 不接 OF |
| `smc_state` | 不接 SMC |
| `htf_leftover` 的 CONTACT/ABOVE/BELOW | 不准当过滤、不准当结局 |
| `htf_living` | 当前盒子问法已关 |
| `T_FX_VISIBLE` | 不是首次可见钟 |
| 1m / aggTrades / 重放 Chan 引擎 | 另起历史 |
| B2 / LTF_B2 | Fact Tape 无此字段；不准补算 |

出生行的 `S0.*` 是当时可见信息，不是未来。

---

## 3. Setup 重叠

2342 个 Candidate 在时间上首尾相接：下一个 `ltf_fx_id` 的首次出现，通常就是上一个的 `FX_IDENTITY_CHANGE`。

规则：

```
每个 setup 的观察窗 = (T_SETUP_VISIBLE, T_OUTCOME_VISIBLE]
第一次事件一旦成立，立即停止
后面的 Tape 行不再属于这个 setup
```

因此：

- 不准把同一个更晚的 B1_LOCK 记到之前所有 setup 上。
- 不准把「最终走到 B2」回溯成这条 setup 的结局。
- 出生行上的 `b1_lock` 不属于这个 setup 的未来（它不是 `t > T_SETUP_VISIBLE`）。

同一根 K 若既是 setup A 的结局行、又是 setup B 的出生行：A 可读这根；B 只把它当 S0，不当自己的 Outcome。

---

## 4. 基数：一个 Setup → 恰好一个 Outcome

```
一个 setup_id  →  恰好一条 Natural Outcome
```

不准输出事件列表。不准「既 continues 又 B1」。  
分类只有一个 `outcome_class`。事件只有一个 `outcome_event`。

B1 是附加标签，不是第二条 Outcome。

---

## 5. 第一事件词汇与分类

同一行若多个条件同时真，**只取最高优先级**（自上而下）：

```
1. BI_DIR_CHANGE     S0.bi_dir ∈ {UP,DOWN} 且 本行 ltf_bi_dir 是另一个 {UP,DOWN}
2. BI_SURE_OFF       S0.bi_sure == True  且 本行 ltf_bi_sure == False
3. BI_SURE_ON        S0.bi_sure == False 且 本行 ltf_bi_sure == True
4. FX_IDENTITY_CHANGE 本行 ltf_fx_id 非空且 ≠ setup_id
                      或本行不再是有效分型（ltf_fx 空 / 非 TOP|BOTTOM）
5. CENSOR            Tape 结束
```

`b1_lock` **不进入** 这张优先级表。它不是目标函数，不准靠抢第一事件变成「成功」。

`outcome_class` 由 `outcome_event` 机械映射，人工不得改口：

| outcome_event | outcome_class | 含义 |
|---------------|---------------|------|
| BI_SURE_ON | CONTINUES | 观察开始后，笔在同方向上确认 |
| BI_DIR_CHANGE | REVERSES | 观察开始后，笔方向先反了 |
| BI_SURE_OFF | DISSOLVES | 已确认的笔被撤回 |
| FX_IDENTITY_CHANGE 且 S0.bi_sure==False | DISSOLVES | 笔未确认，分型身份已离开 |
| FX_IDENTITY_CHANGE 且 S0.bi_sure==True | NEXT_EVENT | 笔已确认，下一分型开始 |
| CENSOR | CENSOR | 样本右删失，不是失败 |

**顶/底分型交替不得叫 REVERSES。** 缠论 15m 分型按构造就会 TOP↔BOTTOM。那是 `FX_IDENTITY_CHANGE`，不是笔反转。

---

## 6. B1 / B2 只做标签

```
label_b1 = 观察窗 (T_SETUP_VISIBLE, T_OUTCOME_VISIBLE] 内
           是否存在一行 b1_lock==true
           且该行 t > T_SETUP_VISIBLE
label_b2 = UNAVAILABLE
```

`label_b1=true` ≠ 成功。`label_b1=false` ≠ 失败。  
不准定义 hit rate、不准把 B1/B2 当 y。  
B2 不在 Fact Tape 上。本 ID **不准**为了标签去跑 BSP/B2。要 B2 只能开新 ID 并另写 Tape 合同。

因窗口在第一次结构事件处关闭，同一 `b1_lock` 行最多打在一个 setup 上。

---

## 明确不做

| 不做 | 原因 |
|------|------|
| 胜率 / PF / expectancy / Entry / Stop | 交易层 |
| MFE / MAE / 最大上下 excursion | 本 ID 无价格路径；且像收益 |
| 按 leftover=1..10 分层 | 顺序是 Outcome → 再问空间是否改变环境 |
| OF / SMC | 尚未轮到增量 |
| 把 2342 当交易 Setup | Census 已说明这是高频观察态 |
| 改 001 Tape 或改 2342 母集 | 基准漂移 |
| 阈值 / 过滤后再数 Outcome | 猎结果 |

授权 Replay 之后才允许只读扫描，只报告：

```
outcome_event 计数
outcome_class 计数
label_b1 计数（不是命中率）
CENSOR 计数
T_OUTCOME_VISIBLE − T_SETUP_VISIBLE 的寿命分布
```

仍然不报告盈亏。

```
Fact Tape
   ↓
Setup_CANDIDATE          已冻 2342
   ↓
Natural Outcome          ← 本 ID 合同
   ↓
（以后）分层是否存在
   ↓
（以后）SMC 是否解释层内差
   ↓
（以后）OF 是否有增量
```
