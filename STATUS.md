# Project Status

## Board — FROZEN STOP

这条「缠论 → OB/FVG → OF」链已经收口。边界：[`research/RESEARCH_BOUNDARY.md`](research/RESEARCH_BOUNDARY.md)

```
CHAN_2BUY_OF_001          CLOSED / PASS
LIFECYCLE_ENTRY_001       CLOSED / STRUCTURAL_NEGATIVE
HTF_FORMING_PEN_CONTEXT   CLOSED / NEGATIVE_AS_OBSERVATION
CHAN_OBSERVATION_STATE    CLOSED / S1–S4 only; LEAVE→Observation 解释已降级
CHAN_LOCATION_001         CLOSED / STRUCTURAL_NEGATIVE
Observation               NOT FOUND on CChan S1–S4
                          own-engine: ALIGNED; Observation NOT DEFINED
Location                  NO INCREMENTAL EDGE
OF                        BLOCKED
Nautilus                  BLOCKED
ARCHITECTURE_BOUNDARY     FROZEN  (Truth/Context/Opportunity/Location/Trigger)
RESEARCH_HYPOTHESIS_001   H1–H5 CLOSED; no H6
STRUCTURAL_DECAY_001      CLOSED / STRUCTURAL_NEGATIVE
STRUCTURAL_OVERLAP_001    CLOSED / STRUCTURAL_NEGATIVE
STRUCTURAL_EFFORT_001     CLOSED / STRUCTURAL_NEGATIVE
H5                        CLOSED; failed_at=identity; no OF
OWN_CHAN_ZS_001           CLOSED / ENGINE_IDENTITY_PASS  (FX 右K走完；≠ Opportunity)
CHAN_PEN_ZS_ENTRY_001     Phase A KEEP / CLOCK_IDENTITY_PASS
                          Phase B/C INVALID OBJECT  (LEAVE ≠ B1/B2)
CHAN_BSP_ALIGN_001        ALIGNED / Observation NOT DEFINED  (停，不再挖 B1 前)
CHAN_B2_OF_LEAD_001       SUPERSEDED → CHAN_B1_B2_EARLY_001
CHAN_B1_B2_EARLY_001      Phase A PRE_B2_WINDOW_EXISTS
                          Phase B OF lead 冻结闸门 PASS ≠ Entry
                          detector BLOCKED
Observation Layer         STOP  (不再找 B1 前 Observation Open)
Opportunity               NOT ESTABLISHED on old CChan S1–S4
                          PEN_ZS B/C 不得引用为「缠论无 Observation」
OF                        BLOCKED
```

H1 Phase A SMOKE-60D：**STRUCTURAL_NEGATIVE / CLOSED**。两个独立失败都成立：

1. **身份不成立** — commit 后 span 仍改写 673 次；同一 decay_id 重复 Open 47；start_jump 3。不能当稳定在线离散事件。
2. **即使忽略身份，结构也不稀疏** — 201 episode / 104 Open；可比较 episode 里 86% 会发生 decay，77% 在第 2 笔。`span_k < span_{k-1}` 是下跌笔的常见几何，不是「正常下跌 → 值得观察」的跃迁。

没有靠 0.618 / 百分位 / 其他阈值救它。不进 OF。不准重开 H1。

H2 Phase A SMOKE-60D：**STRUCTURAL_NEGATIVE / CLOSED**。合同：[`research/structural_overlap/STRUCTURAL_OVERLAP_001.md`](research/structural_overlap/STRUCTURAL_OVERLAP_001.md)。Log: `logs/structural_overlap/STRUCTURAL_OVERLAP_001/SMOKE-60D/`

几何能自然冻结，但对象不成立：

1. **密度** — eligible 70 / Open 59，open|eligible=0.843；73% 在 k=2。
2. **身份** — range_mutation 954；重复 Open 28；start_jump 3。没有用 `is_sure` 补。
3. **自然性** — 100% Open 所在 episode 有 ZS_BORN；83% 同一根 5m。中枢换皮。
4. **因果** — PASS（不能救上面三项）。
5. **事后路径** — Open 后下一下跌笔仍创新低 0.895。普通穿回，不是新状态。

PHASE_A_PASS ≠ Alpha。这里连 PASS 都没有。不准重开 H2。不准进 OF。

**可以自然定义 ≠ 值得作为 Observation State。** H1+H2 共同负结果已冻进 [`research/RESEARCH_BOUNDARY.md`](research/RESEARCH_BOUNDARY.md)：单纯下跌几何变化不足以构成稀疏、稳定、独立于中枢的 Opportunity State。

H5 Phase A SMOKE-60D：**STRUCTURAL_NEGATIVE / CLOSED**。合同未改。`failed_at=identity`。

| Gate | 结果 |
|------|------|
| Causality | PASS |
| Push identity | FAIL — begin/end/span mutation **673**，start_jump 3 |
| Volume identity | FAIL — kl_begin/end/n_bars mutation **673** |
| Effort stability | FAIL — volume_sum mutation **673** |
| Duplicate | FAIL — 7 |
| Density | PASS — 不得翻案。open\|eligible=0.149 |
| H1 overlap | PASS — 不得翻案。frac=0.364 < 0.90 |
| ZS coexistence | PASS — 不得翻案 |

673 与 H1 span_mutation 次数相同。H5 没有更稳的 push 身份。不准用「更稀疏」继续。不准进 OF。

几何变化（H1/H2）与 effort/result（H5）在当前 5m Chan 上均无法给出稳定稀疏 Opportunity State。H1 与 H5 的 mutation 同为 673：同一 forming push 容器被重写。H5 没有修好 H1。

自写引擎 `OWN_CHAN_ZS_001` INC-SMOKE-60D-FXFIX：**ENGINE_IDENTITY_PASS / CLOSED**。合同：[`research/own_chan_zs/OWN_CHAN_ZS_001.md`](research/own_chan_zs/OWN_CHAN_ZS_001.md)。不是 H6。`check_fx` 右 K 走完再分型后：`bi_disappeared=0`，区间/中枢 zgzd 仍 0 次改写。修前 SMOKE-60D 是末笔 `is_sure` 收回 7 次。PASS ≠ Opportunity。不准接 OF。不准重开 H1/H5。

`CHAN_PEN_ZS_ENTRY_001` **Phase A KEEP**；**Phase B/C INVALID OBJECT**。合同：[`research/chan_pen_zs_entry/CHAN_PEN_ZS_ENTRY_001.md`](research/chan_pen_zs_entry/CHAN_PEN_ZS_ENTRY_001.md)。

`CHAN_BSP_ALIGN_001` **ALIGNED**。合同：[`research/chan_bsp_align/CHAN_BSP_ALIGN_001.md`](research/chan_bsp_align/CHAN_BSP_ALIGN_001.md)。B1 前 Observation NOT DEFINED。不再挖 LEAVE / ③。

`CHAN_B1_B2_EARLY_001` Phase A **PRE_B2_WINDOW_EXISTS**。SMOKE-60D-15M：n_lock=5，5/5 有 `t_test_forming < T_B2_truth`（p50=14 根 15m）。身份/因果 PASS。≠ Early Entry。OF / Phase B **BLOCKED**，待授权。合同：[`research/chan_b1_b2_early/CHAN_B1_B2_EARLY_001.md`](research/chan_b1_b2_early/CHAN_B1_B2_EARLY_001.md)。

架构冻结：[`research/ARCHITECTURE_BOUNDARY.md`](research/ARCHITECTURE_BOUNDARY.md)

```
Truth      PASS   (CChan T1/T2 太晚；own-engine B1 对齐中)
Context    PASS   (forming 太宽)
Opportunity NOT ESTABLISHED on old chain; B1 前 Observation STOP
            B1→B2 early: CHAN_B1_B2_EARLY_001 CONTRACT, replay BLOCKED
Location   无增量
Trigger    BLOCKED
```

旧链 Chan = Context / Truth，不是 Opportunity Trigger。不准开 H6。不准接 OF。不准再挖 5m Chan span / overlap / effort。  
自写引擎下一问是 `CHAN_B1_B2_EARLY_001` Phase A（B2 Truth Timing），不是 B1 前 Observation，也不是离开条件。

```
Chan     结构真值成立；CChan Observation ❌；own B1 前窗口未对齐
Location 机械定义成立；对 1→2 无空间增量
OF       尚未测试；不得救场
```

**不要写成：** 缠论完全不提供 1 买前 Observation。证据只覆盖已审计的 S1–S4 空间。  
**不要写成：** OB/FVG 实现失败。失败的是独立空间层没有超过市场覆盖率的增量。  
**不要写成：** 下一步加 OF 过滤 Location。那是改研究对象。  
**不要写成：** 再开 H6 就能补上 Opportunity。那是 hypothesis mining。

B1 前 Observation 链停。若继续：只跑 `CHAN_B1_B2_EARLY_001` Phase A，拆 `T_B2_truth`，不要补旧链。

---

## ARCHITECTURE_BOUNDARY — FROZEN

[`research/ARCHITECTURE_BOUNDARY.md`](research/ARCHITECTURE_BOUNDARY.md)

| 层 | 裁决 |
|----|------|
| Truth | PASS（T1/T2 太晚） |
| Context | PASS / useful（forming 太宽） |
| Opportunity | NOT ESTABLISHED |
| Location | 无空间增量 |
| Trigger / OF | BLOCKED |

不准开 H6。不准为 OF 重定义 Opportunity。

---

## STRUCTURAL_DECAY_001 — STRUCTURAL_NEGATIVE / CLOSED

合同：[`research/structural_decay/STRUCTURAL_DECAY_001.md`](research/structural_decay/STRUCTURAL_DECAY_001.md)  
Log: `logs/structural_decay/STRUCTURAL_DECAY_001/SMOKE-60D/`

H1 裁决：两个独立失败都成立。没有阈值救援。不进 OF。不准重开。

## STRUCTURAL_OVERLAP_001 — STRUCTURAL_NEGATIVE / CLOSED

合同：[`research/structural_overlap/STRUCTURAL_OVERLAP_001.md`](research/structural_overlap/STRUCTURAL_OVERLAP_001.md)  
Log: `logs/structural_overlap/STRUCTURAL_OVERLAP_001/SMOKE-60D/`

H2 裁决：几何可冻，对象不成立。Density / Identity / Naturalness 失败；Causality PASS 不能救。Naturalness 最致命：穿回与中枢同根。没有阈值救援。不进 OF。不准重开。

## STRUCTURAL_EFFORT_001 — STRUCTURAL_NEGATIVE / CLOSED

合同：[`research/structural_effort/STRUCTURAL_EFFORT_001.md`](research/structural_effort/STRUCTURAL_EFFORT_001.md)  
Log: `logs/structural_effort/STRUCTURAL_EFFORT_001/SMOKE-60D/`

H5 裁决：`failed_at=identity`。Causality PASS。Push / volume / effort mutation 均为 673。密度与 H1 overlap 即使 PASS 也不得翻案。不进 OF。

---

## CHAN_LOCATION_001 — STRUCTURAL_NEGATIVE / CLOSED

合同：[`research/chan_location/CHAN_LOCATION_001.md`](research/chan_location/CHAN_LOCATION_001.md)  
Log: `logs/chan_location/CHAN_LOCATION_001/SMOKE-60D/`

Phase 0/1：**机械合同成立**（因果、生命周期、覆盖）。Location 是高密度空间描述层，不是稀疏交易机会层。

Phase 2 SMOKE-60D（只读 overlay；`locations.jsonl` 未改写；无 WR/PF）：

```
n_t1=26  n_t2=33
T1 wick/body/close  0.962 / 0.731 / 0.654
T2 wick/body/close  0.909 / 0.727 / 0.606
base                0.875 / 0.744 / 0.653
T1 lift             1.099 / 0.982 / 1.001
T2 lift             1.039 / 0.977 / 0.928
threshold           1.10  (frozen before overlay)
decision            STRUCTURAL_NEGATIVE
```

T1 wick lift=1.099 不是「差一点就 PASS」。全体 5m 已有 87.5% wick-touch 某条 ACTIVE Location；T1 只是在这个高覆盖上再多一点。close 与 baseline 几乎相同。

Location 侧：7740/9006 时间上从不碰到 T1。碰到的多数是长寿命对象盖住了结构 bar，不是被 T1 选中。T1 结构 bar 相对 Location 的 wick 分类以 **below** 为主（684 below / 52 inside）。`T_lock − t_struct` p50 ≈ 258 根 5m，锁定时钟不能替代结构 bar。

**不要开 OF / Nautilus 来过滤这个对象。** 空间层本身没有增量。

Phase 1 数字（仍成立，不是 Phase 2 的反证）：

```
FVG created  4503
OB created   4503
causality    PASS
duration p50=9  next-bar inv=0.131  coverage=0.9999
concurrent p50=103
decision PHASE1_PASS  ≠ LOCATION_PASS
```

---

## CHAN_OBSERVATION_STATE_001 — CLOSED

合同：[`research/chan_observation_state/CHAN_OBSERVATION_STATE_001.md`](research/chan_observation_state/CHAN_OBSERVATION_STATE_001.md)  
Log: `logs/chan_observation_state/CHAN_OBSERVATION_STATE_001/SMOKE-60D/`

不是 Entry。不是预测 1 买。Observation Open **NOT DEFINED**。

SMOKE-60D Phase A（5m 17279, gaps 0; online PASS）:

```
forming_down_bars  15306/17279   ← 仅“forming down”本身 trivial（Gate D）
episodes unique start_bi  134
EPISODE_OPEN  240  (same start_bi can reopen)
ZS_BORN 42  ZS_EXPAND 28  NEW_BI 164  NEW_LOW 1027
LEAVE_BELOW_ZD 126  REENTER_ZS 239  PRICE_VS_ZS 123
episode overlay in [first,close]: NO_T1=127  T1_NO_T2=0  T1_T2=7
  (T1_lock 常在 forming 结束后才出现，此 join 会低估 T1；不是 Observation 结论)
pre_t1 on identity at lock: NEW_BI 0.92  NEW_LOW 0.88  ZS_BORN 0.31  LEAVE 0.08
```

没有选定任何 event 为 Observation Open。

### Phase B — STRUCTURAL_TRANSITION_AUDIT / COLLECTING

不是 detector。T1/T2 只在最后 join。n_runs=240（OPEN→CLOSE，含 reopen）。

```
first     NEW_LOW 0.525 lead_p50=1     太密，不是 Observation
          ZS_BORN 0.171 lead_p50=66
          REENTER 0.213 lead_p50=67    density_p50=0（多数 run 从不 REENTER）
          LEAVE   0.150 lead_p50=60
combo     LEAVE_THEN_REENTER 0.142
          REENTER_CUR_BI_UP  0.000     回到 ZS 时 last bi 仍是 DOWN
price     BELOW_ZD→IN_ZS 135   IN_ZS→BELOW_ZD 125   IN_ZS→ABOVE_ZG 119
outcome   NO_T1=212  T1_T2=28  （label only）
```

REENTER 比 NEW_LOW 更有结构语义，但仍 **不是** Observation Open。没有自然单点跃迁被选定。

### Phase C — OBSERVATION_STATE_WINDOW_AUDIT / COLLECTING

不预定义 REVERSAL_ATTENTION。T1/T2 最后 join。

```
ZS_REENTERED     43/240 = 0.179
first window p50 3 ×5m
1-bar window     0.30
then ZS_LEFT     0.98     ← 离开→再进入后几乎都会再次跌出，不是稳定观察区间
NEW_LOW rate     0.077 → 0.031（减弱，但窗口站不住）
outcome overlay  had_reenter NO_T1=31 T1_T2=12；无 reenter NO_T1=181 T1_T2=16
```

没有把 ZS_REENTERED 写成 Observation Open。**Phase C Decision: STRUCTURAL_NEGATIVE / CLOSED。** 生命周期不够稳定，无法承担 Observation Layer 的时间容器。本 ID 停止。不接 Location / OF / Nautilus。

---

## HTF_FORMING_PEN_CONTEXT_001 — CLOSED / NEGATIVE AS OBSERVATION CONTEXT

合同：[`research/chan_htf_forming_pen/HTF_FORMING_PEN_CONTEXT_001.md`](research/chan_htf_forming_pen/HTF_FORMING_PEN_CONTEXT_001.md)

负结果（有价值）：Context 不能承担 Observation 的职责。不要再为 Coverage 写新 detector。

```
             Online   Identity      Coverage   Needs_Sure
15m forming  PASS     EXPLAINABLE   0.651      NO
30m forming  PASS     EXPLAINABLE   0.582      NO
1h  forming  PASS     EXPLAINABLE   0.584      NO
```

1. 实时性成立：三档都能在未 sure 时在线获得。不是「必须等线段确认」。
2. Identity 成立：`start_jump=0`；endpoint 更新不是新 Context；方向变化才 replacement。
3. 不足以当 Observation Context：Coverage ≈ 0.58–0.65；提高 TF 没有解决覆盖。禁止 `HTF DOWN forming pen = 潜在 1BUY`。

15m / 30m / 1h 都是 Candidate Context，都不是 1BUY Context。本 ID 停止。不选 TF。不定 Observation。不定 Entry。

Logs: `SMOKE-60D` / `SMOKE-60D-30M` / `SMOKE-60D-1H`

---

## CHAN_LIFECYCLE_ENTRY_001 — CLOSED (`STRUCTURAL_NEGATIVE`)

```
Decision               STRUCTURAL_NEGATIVE / CLOSED
1BUY_PRECONDITION      PASS
Lifecycle Identity     VALID
Lifecycle Boundary     VALID
Maturation             NOT AVAILABLE
ENTRY                  NOT AVAILABLE
Location/OF/Nautilus   BLOCKED
Detector               STOPPED
```

Not an implementation failure. Under `chan.py` + 5m + `1BUY_PRECONDITION` + `(start_bi, zs_begin, zs_end)`, `LIFECYCLE_OPEN` is already past leave / T1 geometry. No natural Maturation → Entry.

**This ID is finished.** Do not write another detector. Do not add +N bars. Do not open Location / OF / Nautilus here. Do not reverse from OF to invent an entry.

If a later ID opens: do not start from OF / FVG / detector. Only question is the forming-down-segment state change that can legally open Observation. That state is not predefined.

Contract: [`research/chan_lifecycle_entry/CHAN_LIFECYCLE_ENTRY_001.md`](research/chan_lifecycle_entry/CHAN_LIFECYCLE_ENTRY_001.md)

Audits:
- [`BSP_CONFIG_AUDIT.md`](research/chan_lifecycle_entry/BSP_CONFIG_AUDIT.md)
- [`LIFECYCLE_BOUNDARY_AUDIT.md`](research/chan_lifecycle_entry/LIFECYCLE_BOUNDARY_AUDIT.md)
- [`LIFECYCLE_BOUNDARY_RETRACE.md`](research/chan_lifecycle_entry/LIFECYCLE_BOUNDARY_RETRACE.md)
- [`LIFECYCLE_MATURATION_AUDIT.md`](research/chan_lifecycle_entry/LIFECYCLE_MATURATION_AUDIT.md)

### SMOKE-60D-MATURATION (accepted: no legal Entry on this object)

```
n_t2 33   diagnostic Gate A pass  0/16 candidates
high-coverage flags already true at OPEN and 3/33 SAME_BAR
END_BI_MOVED  0 same-bar but coverage 0.09
ZD/ZG never move inside frozen zs span
Decision STRUCTURAL_NEGATIVE
```

`logs/.../SMOKE-60D-MATURATION/`

### SMOKE-60D-LIFECYCLE (identity episodes; not Entry)

```
OPEN 95  UPDATE 113  CLOSE 95  GEOMETRY_CLOSE 13
close  NEW_ZS 47  SEGMENT_REPLACED 9  ZS_GONE 2  EOS 37
OPEN precondition True/False  51/44   ever True 60/95
duration_closed  median 67  p75 98  max 344   (ex-EOS)
T2 zs_frontier INSIDE 33/33   seg_frontier 14/33
lead_from_OPEN  p25=7 median=86   (not Entry)
Decision COLLECTING  (historical run; ID now CLOSED)
```

`logs/.../SMOKE-60D-LIFECYCLE/`

### SMOKE-60D-BOUNDARY (11 REOPEN; not Entry)

```
SAME_STRUCTURE           1/11   (seg 6; forming-seg recalc; gap=139, not 1-bar)
SAME_SEG_NEW_ZHONGSHU   10/11   (same start_bi, new last 中枢)
1-bar False flicker      0
T2 join max(true_seg)   33/33 inside assigned episode
lead_last p25 (raw OPEN→T2) 161   (not Entry; not Alpha)
Decision                UNRESOLVED
```

Proposed identity (not frozen as Entry): `(down_seg.start_bi, last_zs begin/end)`. `seg_idx` REOPEN ≠ same lifecycle.

`logs/.../SMOKE-60D-BOUNDARY/`

### SMOKE-60D-PRECONDITION (snapshot, not Entry)

```
n_bars              17279
n_true_bars         5461
PRECONDITION_OPEN   34
PRECONDITION_CLOSE  45
PRECONDITION_REOPEN 11
duration_5m         min=1 p25=90 median=3378 p75=11171
ENTRY               NOT AVAILABLE  (ID closed)
Decision            COLLECTING  (historical snapshot run)

Diagnostic Gate A (OPEN bars only; not a Decision)
  coverage 33/33  lead_last p25=152  min=1  diagnostic_overall PASS
```

`logs/.../SMOKE-60D-PRECONDITION/`

34 OPEN vs 33 T2. 11 REOPEN + duration min=1: do not freeze first True as Entry.

Frozen 1-buy (this config): `min_zs_cnt=1` **on the current segment**, multi-bi only; leave must break ZD; `bs1_peak`; MACD 保送 (`divergence_rate=inf`). `get_bsp()` T1 ≠ lock ≠ precondition.

### STUB_NONE (baseline)

```
n_t2_lock 33  NO_ENTRY 33  n_ENTRY_OPEN 0  Decision COLLECTING
```

`logs/.../SMOKE-60D/`

### LIFECYCLE_RETRACE_v0 REJECTED

```
coverage 1.00 PASS  causality PASS  lead_last p25=8 FAIL  n_ENTRY_OPEN=416  OVERALL FAIL
```

### LIFECYCLE_RETRACE_v1 NOT ACCEPTED

```
Gate A PASS  n_ENTRY_OPEN=4  lead_last p25=2457  — wrong object
```

### ZHONGSHU_LIFECYCLE_v0 (sure 中枢, leave below ZD, first reverse)

```
coverage      1.00   PASS
causality     PASS
lead_last_p25 60     PASS  (>= 12)
n_ENTRY_OPEN  108    (416 → 108 → not 4)
lead_last     min=8 p25=60 median=133 p75=271 max=743
lead_first p25 3362  (not a PASS input)
n_false_open  1
OVERALL       PASS
```

`logs/.../SMOKE-60D-ZHONGSHU-v0/`

108 vs 33 T2: 中枢约束压掉了无中枢反弹，仍不是 2买确认。This ID is **CLOSED**; do not continue WAIT_2BUY / Location here.

---

## CHAN_2BUY_OF_001 — CLOSED (Phase 0–2 PASS, Case Entry UNRESOLVED)

| Dimension | Status |
|-----------|--------|
| Phase 0–2 | **PASS** |
| Case Entry | **UNRESOLVED** |
| Phase 3 | **CLOSED** |
| Finding | CChan BSP lock is not a 1BUY→2BUY lifecycle entry (`T_lock(T1)=T_lock(T2)=T0`, 26/26) |
| Successor | **CHAN_LIFECYCLE_ENTRY_001** — now **CLOSED** (`STRUCTURAL_NEGATIVE`) |

Contract remains historical: [`research/chan_2buy_of/CHAN_2BUY_OF_001.md`](research/chan_2buy_of/CHAN_2BUY_OF_001.md)  
Smoke: `logs/chan_2buy_of/CHAN_2BUY_OF_001/SMOKE-60D/`

### SMOKE-60D (counts only)

```
1m  expected 86400 actual 86400 gaps 0
5m  expected 17279 actual 17279 gaps 0
Chan locked T1: 26
Cases total 26  T7 26  INVALID 0  TIMEOUT 0  SUPERSEDED 0  OPEN 0
STATE_VIOLATION 0
Decision: PASS
```

### T2_LOCK_AUDIT (SMOKE-60D, counts / CChan state only)

```
type_contract          PASS  (exact T2 26/26, T2S-only 0, relate_bsp1 26/26)
T2 first locked == T7  FAIL  0/26
T2 already locked @T0  26/26
last_sure_pos T0==T7   24/26
delta_counts           {1: 24, 3: 1, 4: 1}
Decision: INVALID
Phase 3: NOT OPEN
```

Report: `logs/chan_2buy_of/CHAN_2BUY_OF_001/SMOKE-60D/T2_LOCK_AUDIT.txt`

### BSP_CAUSAL_AUDIT (SMOKE-60D, CChan state only)

```
situation_label: A
T2_LOCKED_AT_T0: 26/26
T1 first_lock == T0: 26/26
T2 first_lock == T1 first_lock: 26/26
T2 visible unlocked then locked: 26/26
T2 visible after already lockable: 0/26
Phase 3: NOT OPEN
Contract / Chan Config / T0 / T2: FROZEN
```

000001: T1 vis@445 (sure=83) → T2 vis@496 (sure=83) → both lock@677 (sure jumps to 551) = T0.

Report: `logs/chan_2buy_of/CHAN_2BUY_OF_001/SMOKE-60D/BSP_CAUSAL_AUDIT.txt`

### CASE_ENTRY_AUDIT (design only — no code)

Current `T0 = T1 first_locked` cannot host “OF before 2-buy”: `T_lock(T1)=T_lock(T2)=T0` (26/26).

Viable clocks for the original question: **A** `T_visible(T1)`, maybe **E1** `T1 bi.is_sure`, maybe **F** first callback bi. **C** `T_visible(T2)` is a different experiment (confirmation timing). **B/D** are labels, not entry.

Phase 3: **NOT OPEN**. Contract / Chan config / T0 / T2: **FROZEN**.

Doc: `research/chan_2buy_of/CASE_ENTRY_AUDIT.md`

### CASE_ENTRY_E1_F PROBE (read-only, 26 cases)

```
E1               valid 5/26   median lead 172 bars   invalid: not_after_t1_visible 21
F_rebound_exist  valid 25/26  median lead 245
F_rebound_sure   valid 25/26  median lead 241
F_callback_exist valid 25/26  median lead 237   (== T2 visible 5/26)
F_callback_sure  valid 25/26  median lead 232
Case Entry: UNSELECTED
Phase 3: CLOSED
```

Report: `logs/chan_2buy_of/CHAN_2BUY_OF_001/SMOKE-60D/CASE_ENTRY_E1_F.txt`

---

## MM_EDGE_EXP_001 — CLOSED (FROZEN)

| Dimension | Status |
|-----------|--------|
| Research Phenomenon | **PASS** (conditional markout exists) |
| Economic Edge | **FAIL** |
| Prefill Predictability | **FAIL** (snapshot observability) |
| Strategy | **FROZEN** |
| Execution | **STOPPED** |
| Stage 3 | **LOCKED** |

EXP_001 Prefill strict conclusion:

> Under current **snapshot observability** (~1.66s), no CANDIDATE_V0_2_SIGNAL.  
> This is **NOT** proof that pre-fill signal does not exist in the market.

Weak signals (research observations only — **not** trading filters):

- `depth_total_5`: ±3.8pp Path C separation, Economic gate FAIL
- `obi_change_5s`: +0.00027 USDT/fill economic Δ
- `pre_deteriorated_strict=False`: +0.00116 USDT/fill economic Δ

Reports: `logs/maker_edge/` — see sections below for detail.

---

## MM_EDGE_EXP_002 — Phase 1 LONG-TERM DATA COLLECTION

| Dimension | Status |
|-----------|--------|
| Type | Data Collection / Observability |
| Strategy | **NONE** |
| Trading | **NO** |
| Stage 3 | **LOCKED** |
| Gate 1 | **PASS** (smoke `EXP-002-RUN-001`) |
| Gate 2 | **PASS** |
| Gate 3 | **PASS** |
| Gate 4 | **BLOCKED** |
| Long-run | **EXP-002-RUN-002** via `event-state-probe.service` |

Do **not** Path-C snoop during collection. Frozen Gate 4 sample gates are in `MM_EDGE_EXP_002.md` (set before long-run start).

Spec: `MM_EDGE_EXP_002.md`  
Smoke: `./scripts/smoke_test_event_state.sh`  
Validate: `python scripts/validate_event_ledger.py --dir logs/event_state/EXP-002-RUN-001 --run-id EXP-002-RUN-001`  
Logs: `logs/event_state/EXP-002-RUN-001/`

### EXP-002-RUN-001 Smoke (2026-08-18, ~12 min + restart)

Host: `jADUtR1041803` | Sessions: **2** (restart test) | Schema: `immutable_event_v1`

| Check | Result |
|-------|--------|
| Gate 1 Event Completeness | **PASS** (Phase 1 stream; no fill_anchor) |
| Gate 2 Temporal Integrity | **PASS** |
| Gate 3 Event Coverage | **PASS** |
| Restart contract | **PASS** (0 parse fail, 0 dup event_id, seq reset) |
| Gate 4 | **BLOCKED** |

Write rates:
- `aggressive_trade`: **3.21 / sec** (2300 events)
- `book_update`: **6.09 / sec** (4366 events)
- **total**: **9.30 / sec** (6666 market events)

Timestamp quality (100% exchange + local present):
- `local − exchange` lag: p50 **112.5ms**, p95 **237.7ms**, p99 **251.4ms**, max **443.4ms**
- `exchange > local + 50ms`: **0** violations

Event order (recorded, not sorted):
- `exchange_ts_ns` regressions: **1053** (max back **276ms**) — multi-source async; explicit in report

Raw schema sample (n=200 each): **0% missing** on core fields; **0** hollow book_update.

Manifest: `logs/event_state/EXP-002-RUN-001/EXP-002-RUN-001.manifest.json`  
Report: `logs/event_state/EXP-002-RUN-001/Event_Ledger_Validation.json`

Long-run identity: **EXP-002-RUN-002** (separate from smoke). Status: `./scripts/event_state_status.sh`

---

## MM_EDGE_EXP_001 Detail

**Phase: Prefill Adverse-Selection Attribution v0.1** (probe **STOPPED**)

| Gate | Status |
|------|--------|
| Research Freeze | **ACTIVE** |
| Probe | **STOPPED** |
| Data Integrity | **PASS** |
| Maker-only | **PASS** (`TAKER=0`) |
| Account Reconciliation (RECON-01) | **PASS** |
| RECON-02 classification | **PASS** |
| Order-level closure (RECON-03) | **PASS** |
| Strict trade-level closure | **FAIL** (Testnet userTrades cutoff — **not** Alpha FAIL) |
| Economic Edge | **FAIL** (current execution economics) |
| Prefill Predictability (v0.1 strict) | **FAIL** (no CANDIDATE_V0_2_SIGNAL) |
| Stage 3 | **LOCKED** |

## Evidence taxonomy (4777 fills)

| Class | Count | Grade |
|-------|-------|-------|
| **MATCHED** | 3890 | Order + Trade (dual) |
| **VENUE_CONFIRMED_NO_TRADE_HISTORY** | 876 | Order FILLED, no trade row |
| **VENUE_PARTIAL_ORDER_CANCELED** | 11 | Partial fill + TTL cancel |
| DUPLICATE / MISMATCH / UNCONFIRMED | 0 | — |

`userTrades` cutoff: **2026-08-17T03:08 UTC** — see `TESTNET_LIMITATIONS.md`

Matched trade-level: qty residual **0**, |Δt| p50 **72ms**

## Separation

```
MakerAlpha (+0.008%)  ≠  Account Δ (−61.66 = fee + realized)
Strict trade FAIL     ≠  Maker Edge FAIL
887 orphans           =  VENUE-HISTORY-CUTOFF (now order-confirmed)
```

## Economic Attribution v0.1 (Hard Evidence Population only)

Population: **MATCHED=3890**  
Core report: `logs/maker_edge/Economic_Attribution_v0_1.txt`

- Matched fills / paths / clusters: **3890 / 3886 / 3334**
- Fee total: **42.42 USDT**
- Realized component: **−8.52 USDT**
- Gross markout @30s: **−1.73 USDT**
- Net attributable @30s: **−52.67 USDT**
- Inventory carry:
  - Max `|net BTC|`: **0.0059**
  - TW `|net BTC|`: **0.0035**
  - Turnover: **3.3316 BTC**

Counterfactual Attribution:
- Baseline matched net30: **−52.67 USDT**
- Exclude `Path C`: **−21.22 USDT**
- Exclude toxic: **−21.22 USDT**
- Exclude negative states: **−27.64 USDT**

Interpretation:
- v0.1 已完成 baseline 使命：**Maker markout phenomenon exists, economic edge not established**
- 当前主要拖累不是“假 alpha”，而是 **fee + realized / inventory economics**

## Metric Reconciliation (MATCHED=3890)
- Return-space MakerAlpha（fill-weighted）：-0.000693%
- Return-space MakerAlpha（notional-weighted）：-0.000816%
- Dollar-space gross markout @30s：-1.730780 USDT
结论：回报口径一致，但“加权方式”导致返回与美元金额的方向差异。

## Fee Sensitivity (counterfactual, fee only)
net_attr_30s @fee_factor:
  1.00 → -52.674655 USDT
  0.50 → -31.463582 USDT
  0.25 → -20.858046 USDT
  0.10 → -14.494724 USDT
  0.00 → -10.252510 USDT
结论：即使假设 0 fee，net 仍 < 0，因此“真实拖累”不仅是 fee。

## Prefill Adverse-Selection Attribution v0.1 (strict contract)

Population: **MATCHED paths = 3886** (100% strict-prefill coverage)  
Core report: `logs/maker_edge/Prefill_Adverse_Selection_Attribution_v0_1.txt`

Time contract: `feature_timestamp <= t_fill - 0.25s`  
Feature source: sampled `mid_tick` / `inventory_tick` only (no fill-callback leakage)

Baseline (strict population):
- P(Path C): **33.20%**
- P(Toxic): **34.61%**
- P(Neg30s): **47.43%**
- P(Economic<0): **77.61%**
- Mean net_attr_30s: **−0.0136 USDT/fill**
- Feature age: mean **1681ms**, median **1660ms**

Conclusion Matrix (auto-grade):
- **CANDIDATE_V0_2_SIGNAL**: **0 / 19 features**
- **STATISTICAL_SIGNAL_ONLY**: spread_change_5s (Toxic/Neg30s), inventory/inventory_skew (Economic only)
- **NO_PREFILL_SIGNAL**: all others under strict gate

Unavailable under strict contract (deferred to EXP_002):
- `time_since_last_market_event`, intensity, large trades, fill-callback `market_event_before_fill`

## Forbidden (both experiments)

- Resume EXP_001 probe without new experiment ID
- Enable trading under EXP_002
- Reclassify VENUE_CONFIRMED as MATCHED
- Unlock Stage 3 on observability or attribution alone
- Treat STATISTICAL_SIGNAL_ONLY as v0.2 candidate
