# CHAN_HTF_ZS_LTF_B1_001

```
Experiment:     CHAN_HTF_ZS_LTF_B1_001
Type:           HTF 笔中枢 Location × LTF B1/B2 结构  只读审计
                (not detector, not strategy, not OF, not HTF BSP)
Engine:         user_data/Chan
HTF object:     cal_bi_zs_list_pure  已经存在的笔中枢  (zg / zd)
LTF object:     find_all_bsp  B1 = SETUP，B2 = CONFIRM / Entry 真值
Predecessor:    旧链 CLOSED，本 ID 不继承
                CHAN_LOCATION_001  CLOSED（5m OB/FVG 过密，无增量）
                CHAN_B1_B2_EARLY_001  OF lead 独立性失败；15m B2 仍可作 LTF 标签
                OWN_CHAN_ZS_001  zg/zd 出生即冻（引擎事实，不是本 ID 的 PASS）
                CHAN_BSP_ALIGN_001  LTF B1/B2 代码语义
Why opened:     高周期 B1 不能做低周期 B1 的实时 Context（时间倒挂）。
                真正可能提供增量的是：已经存在的 HTF 笔中枢告诉 LTF B1 在哪里发生。
Phase:          0  PASS / SPACE_OBJECT_EXISTS
Active:         NO。当前盒子问法关闭。见 CHAN_HTF_HIST_ANCHOR_LTF_B1_001
Replay:         Phase 0 DONE。不准再拿 living 盒子比较 B1→B2
OF:             BLOCKED on this ID
SMC:            不是第二套 WHERE。本 ID 只提供 Macro 空间
HTF B1 / B2:    FORBIDDEN
H1–H5 / H6:     stay CLOSED
5m FVG Location: FORBIDDEN（不同对象，已关闭）
Success / WR / PF: FORBIDDEN
```

本 ID 是新问题。  
不准把旧链的 Observation / OF lead / Location 覆盖率当成前置 PASS。

---

## Hypothesis

> 低周期 B1 若发生在**已经存在**的高周期笔中枢关键区域，其结构意义是否不同于发生在高周期中枢之外？

「已经存在」= 高周期中枢在高周期 B1 之前、也在低周期 B1 之前，就已经在线可知。  
不是等高周期 B1。

---

## Causal clock (this ID)

```
高周期中枢形成                         ← HTF Location 上线
      │
      │  关键价格区域已经在线存在
      │
      ▼
价格进入 / 接近高周期中枢关键区域
      │
      ▼
低周期 B1                              ← SETUP
      │
      ▼
低周期 B2                              ← CONFIRM / Entry 真值
```

分层：

```
HTF ZS          WHERE / Location
LTF B1          SETUP
LTF B2          CONFIRM
ENTRY           只允许钉在 LTF B2，本阶段仍 FORBIDDEN
```

---

## Forbidden clock

```
高周期 B1
      ↓
低周期 B1
```

时间倒挂：

```
LTF B1 ────────────────→
             HTF B1 ───→
```

HTF B1 只能做事后多周期共振标签。  
本 ID **完全不使用** HTF B1 / HTF B2。

---

## Why this is not CHAN_LOCATION_001

| | 已关闭的 Location | 本 ID |
|--|------------------|--------|
| 对象 | 5m OB/FVG | HTF `cal_bi_zs_list_pure` 笔中枢 |
| 密度 | 自己大量产生，覆盖 87.5% | 低频、结构性、有 zg/zd 边界 |
| 增量问题 | 几乎到处都有 Location | 中枢内 / ZG 附近 / ZD 附近 / 中枢外 是否不同 |
| 与 B1 的关系 | 覆盖 B1 不等于解释 B1 | HTF 区域是否改变随后 LTF B1 的结构意义 |

例子（**默认审计组合，未冻结为唯一组合**）：

```
1H 笔中枢
ZG ─────────────────
        ↓
     15m 下跌
        ↓
     接近 ZD
        ↓
      15m B1
        ↓
      15m B2
ZD ─────────────────
```

问的不是「HTF B1 是否领先 LTF B1」。  
问的是：「一个已经存在的 HTF 笔中枢，其空间位置是否能给随后出现的 LTF B1 提供增量信息？」

---

## Truth (frozen)

HTF 与 LTF 各自跑完整管线，互不拿对方的 BSP。

```
HTF:  因果闭合 HTF bar
      klu → klc → cal_bi_list → cal_bi_zs_list_pure
      只用笔中枢。禁止 find_all_bsp / find_first_bsp / 线段中枢

LTF:  因果闭合 15m bar
      klu → klc → cal_bi_list → cal_bi_zs_list_pure → find_all_bsp
      B1 / B2 定义与 CHAN_BSP_ALIGN_001 相同
```

LTF 标签（只作本 ID 的结构钟，不继承 EARLY_001 的 OF 结论）：

| 标签 | 代码 |
|------|------|
| B1 | `leave` DOWN ∧ `check_bi_div` ∧ `zs.is_sure` |
| B2 | 同一背驰；`bounce=leave.next`；`second=bounce.next`；`second.is_sure` ∧ `second.end_klc.low > leave.end_klc.low` |
| B1_LOCK | B1_VISIBLE ∧ `leave ∉ zs.bi_list` |
| T_LTF_B1 | 第一次 B1_LOCK 的闭合 15m |
| T_LTF_B2 | 第一根闭合 15m 上 `find_all_bsp` 已发出该 zs 的 B2，且本案仍 B1_LOCK |

禁止 `find_first_bsp`。禁止线段中枢。禁止改引擎。

---

## HTF 中枢：什么时候第一次在线可知

身份键：`zs.start_bi.start_time`（与 OWN_CHAN_ZS_001 相同）。

| 时刻 | 定义 |
|------|------|
| `T_HTF_ZS_VISIBLE` | 第一根**已收盘 HTF bar**，其前缀 `cal_bi_zs_list_pure` 已发出该 zs |
| 出生条件 | 连续三笔 `is_sure`，方向交替，`zg > zd` |
| 出生时的区间 | `zg = min(bi.high × 3)`，`zd = max(bi.low × 3)` |
| 因果 | 只用 `HTF.close <= t`。LTF B1 出现时，HTF 不得读未来 HTF bar |

`T_HTF_ZS_VISIBLE` 必须 **严格早于** `T_LTF_B1`。  
否则该 HTF 中枢不是这笔 LTF B1 的前置 Location。

末中枢 `is_sure` 跟随 `bi_list[-1].is_sure` 会闪。  
那是确认标志，不是 zg/zd。审计要分开记，不能把 `is_sure` 闪烁写成「中枢还不存在」。

---

## ZG / ZD 是否稳定

引擎事实（OWN_CHAN_ZS_001，本 ID 只引用，不重判 Opportunity）：

- 确认笔一旦 `is_sure`，high/low/dir/start 冻
- `cal_bi_zs_list_pure` 出生的 zg/zd **冻**
- `bi_list` 允许延伸；gg/dd 可变
- 末中枢 `is_sure` 允许随最后一笔翻转

本 ID 审计时仍要在 **HTF 时钟**上复核：

1. 同一 identity 的 zg/zd 在 `T_HTF_ZS_VISIBLE → T_LTF_B1` 是否改写
2. 该 zs 是否消失后又用同一 start 重生
3. 延伸是否只加成员、不改 zg/zd

任一改写 → 该 HTF 中枢不能当 Location。不是去改 `cal_bi_zs_list_pure`。

---

## LTF B1 落点（相对已有 HTF 中枢）

在 `T_LTF_B1`，取当时在线的 HTF 中枢（`T_HTF_ZS_VISIBLE < T_LTF_B1` 且仍在列表）。

价格锚：LTF B1 的 `leave.end_klc.low`（与 B2 比较字段一致）。  
同时记录 `leave.end_klc.high`，但分桶以 low 为主。

先记连续量，**不准先发明「附近」阈值**：

| 量 | 定义 |
|----|------|
| `d_zd` | `leave.end_klc.low - zd` |
| `d_zg` | `zg - leave.end_klc.low` |
| `width` | `zg - zd` |
| `pos` | `(leave.end_klc.low - zd) / width`  （0=ZD，1=ZG） |

报告用的粗桶（阈值未冻，只为读分布）：

| 桶 | 含义 |
|----|------|
| `INSIDE` | `zd <= low <= zg` |
| `NEAR_ZD` | 在 ZD 外侧或内侧、距离占 width 的比例（直方图后再冻） |
| `NEAR_ZG` | 对称 |
| `OUTSIDE_BELOW` | `low < zd` |
| `OUTSIDE_ABOVE` | `low > zg` |

若同时有多个仍有效的 HTF 中枢：逐个记账，**主中枢** = 当时 `pos` 离 `[0,1]` 最近的那个；并列则取更早 `T_HTF_ZS_VISIBLE`。不准事后挑「好看的」中枢。

---

## LTF B1 出现时 HTF 中枢是否仍有效

`VALID_AT_B1` 当且仅当同时成立：

1. 该 zs 仍出现在 `T_LTF_B1` 的 HTF `cal_bi_zs_list_pure` 输出
2. identity 未换 start
3. zg/zd 相对 `T_HTF_ZS_VISIBLE` 未改写
4. 不要求末中枢 `is_sure == True`（那是另一列，只报告）

`VALID_AT_B1 = false` 的 LTF B1：**没有** HTF Location，归入 `NO_HTF_ZS`。  
不能把无效中枢硬套进去。

---

## Read-only audit（Phase 0，先做这些，不准跑实验）

只读、定义级。回答下面五问之后才允许谈 replay。

1. HTF 中枢什么时候第一次在线可知？ → `T_HTF_ZS_VISIBLE`
2. 中枢 ZG / ZD 是否稳定？ → HTF 前缀重放，identity 表
3. LTF B1 是否落在：内部 / ZG 附近 / ZD 附近 / 外部？ → `pos` + 粗桶
4. LTF B1 出现时 HTF 中枢是否仍有效？ → `VALID_AT_B1`
5. 完全不使用 HTF B1 / HTF B2。 → 代码与 ledger 不得出现 HTF BSP 字段

默认只读组合（可被下一阶段改，本阶段不要比较多组）：

```
symbol:   BTCUSDT-PERP
HTF:      1H  因果闭合
LTF:      15m 因果闭合
data:     nautilus_mm/data/chan_2buy_of/BTCUSDT-PERP/1m.parquet
```

不同 HTF/LTF 组合 **只有** 在上述结构关系成立之后才值得比较。

---

## Hard gates（以后若授权 replay，顺序不可翻）

后面的数字不能推翻前面的 FAIL。

| 门 | 通过 |
|----|------|
| 1 Causality | HTF/LTF 都只用已收盘 bar；HTF 在 `T_LTF_B1` 不读未来 |
| 2 No HTF BSP | ledger / 代码路径零 HTF B1/B2 |
| 3 ZS existence | `T_HTF_ZS_VISIBLE < T_LTF_B1` |
| 4 ZS identity | 到 B1 为止 zg/zd 不改写、不消失换皮 |
| 5 Location contrast | 中枢内/边界/外部 的 LTF B1→B2 完成率或时钟 **不是**被密度解释掉的同一分布 |

门 5 未做之前，禁止写「HTF 中枢有增量」。  
门 5 的具体统计量本阶段 **不冻**——先看只读样本的落点分布。

全部 PASS ≠ Entry。只表示：HTF 笔中枢作为 Location，相对「LTF B1 随便发生」有结构差。

---

## Forbidden

- 用 HTF B1 当 LTF B1 的 Context
- 接 OF / Nautilus / 重开 H6 / 5m FVG Location v2
- 把 EARLY_001 Phase B 机械 PASS 写成独立 lead
- 本阶段写 runner、改窗口、加过滤器「救」旧链
- 优化 `cal_bi_zs_list_pure` 来打出 Location PASS
- Success / WR / PF / 提前 Entry

---

## Next

当前 living 盒子 × 当时 LTF B1 这条问法关闭。Phase 0 数字不可变。  
下一对象是历史 leftover 锚点，见 `CHAN_HTF_HIST_ANCHOR_LTF_B1_001`。不准在本 ID 上换 TF 找 INSIDE。

---

## SMOKE-60D-1H-15M Phase 0

Log: `logs/chan_htf_zs_ltf_b1/CHAN_HTF_ZS_LTF_B1_001/SMOKE-60D-1H-15M/`

因果前缀：1H `cal_bi_zs_list_pure`（零 BSP）× 15m `B1_LOCK`。未比较 B1→B2。

| 门 | 结果 |
|----|------|
| C0 Size | PASS n_LTF_B1=5 |
| C1 Causality | PASS 全部 `T_HTF_ZS_VISIBLE < T_LTF_B1`；ledger 无 HTF BSP |
| C2 Identity | PASS zg/zd 相对 visibility 未改写 |
| C3 Existence | PASS 5/5 有 prior living HTF ZS；NO_HTF_ZS=0 |
| C4 Spatial | PASS 均可分桶：**INSIDE=0 BOUNDARY_CONTACT=0 OUTSIDE=5** |

Δt：min 6.5h / p50 58h / max 233h。中枢在 B1 之前已经在线。

```
CHAN_HTF_ZS_LTF_B1_001 / Phase 0 = PASS / SPACE_OBJECT_EXISTS
≠ Location 有增量
≠ 可比较 B1→B2
Phase 2 = BLOCKED
```

三个条件：

| 条件 | 本跑 |
|------|------|
| 提前存在 | 成立。5/5 |
| 位置稳定 | 成立。zg/zd 未改写 |
| B1 落在空间关系中 | 成立，但全部是 **OUTSIDE** |

准确说法：1H 笔中枢作为前置 WHERE 对象成立。本窗口里 15m B1_LOCK **没有**落在 living HTF ZS 内部或边界。不能写成「HTF 中枢无效」。也不能写成已经证明 WHERE 改变了 SETUP。

Phase 2 对照桶在本样本是空的。未授权。不准为了找 INSIDE 换周期。
