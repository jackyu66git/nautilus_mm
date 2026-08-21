# CHAN_HTF_ZS_LTF_B1_001 — Phase 0

```
Experiment:     CHAN_HTF_ZS_LTF_B1_001
Phase:          0  PASS / SPACE_OBJECT_EXISTS
Decision:       空间对象成立。全部 OUTSIDE。≠ Location 增量
Replay:         Phase 0 DONE。Phase 1/2 BLOCKED
OF / Entry / B2 完成率:  FORBIDDEN
HTF B1/B2:      FORBIDDEN
Next:           未授权 Phase 2。本样本 INSIDE=0，对照桶空。
```

合同 `CHAN_HTF_ZS_LTF_B1_001.md` **未改**。  
本文件只回答 Phase 0 五问，并记下报告字段。不比较 TF，不接 OF。

---

## Verdict

五问在引擎上都可以无歧义回答。时钟方向正确。  
**不能**写成 Phase 0 PASS。硬门是经验问题：LTF B1 当时，HTF 中枢是否已经作为稳定空间存在。那一步需要因果前缀，当前 BLOCKED。

```
Phase 0  定义能否支撑「HTF ZS 早于 LTF B1」
        │
        ├── 定义失败 → 关闭     （未发生）
        │
        ▼
   DEFINITIONS_CLOSED
        │
        ×  未授权 replay
        │
以后若授权，才量  T_HTF_ZS_VISIBLE < T_LTF_B1
        │
        ├── 大量 B1 当时没有已存在的 HTF ZS → 关闭
        │
        ▼
Phase 1  空间关系是否稳定、可重复
        ▼
Phase 2  才第一次问：同样的 LTF B1 下，HTF 位置是否改变 B1→B2
        │
        ├── 无结构差 → 关闭
        └── 有结构差 → 再考虑 OF
```

Phase 2 之前禁止把「某个位置 B1 很多」写成有价值。

---

## 因果链（本 ID）

```
HTF 笔中枢形成
      │  T_HTF_ZS_VISIBLE
      ▼
已经存在的 HTF 空间          WHERE
      │
      ▼
LTF B1                      SETUP
      │
      ▼
LTF B2                      CONFIRM
```

Entry 暂时 = LTF B2，本阶段仍不算。HTF B1/B2 不在实时链上。

---

## Q1  `T_HTF_ZS_VISIBLE < T_LTF_B1`  — 硬门

**定义（引擎可实现，未计量）**

HTF 只用：

```
klu → klc → cal_bi_list → cal_bi_zs_list_pure
```

禁止 `find_all_bsp` / `find_first_bsp` / 线段中枢 `zs_list`。

`T_HTF_ZS_VISIBLE` = 第一根**已收盘 HTF bar**，其前缀第一次发出该 zs。  
身份键：`zs.start_bi.start_time`。

出生：连续三笔 `is_sure`、方向交替、`zg > zd`。  
`zg, zd = min(high×3), max(low×3)`，见 `cal_bi_zs_list_pure` 397–400 行。

因果：LTF B1 时刻只用 `HTF.close <= T_LTF_B1`。同一根未收盘 1H 不得进 HTF 前缀。

`T_LTF_B1` = 第一次 LTF `B1_LOCK` 的闭合 15m（合同原样）。

硬门：`T_HTF_ZS_VISIBLE < T_LTF_B1`。相等或更晚 → 该 zs 不是这笔 B1 的前置 Location。

同根失败模式：B1 落在「中枢刚出生的那根 HTF 收盘」上。Δt 必须 > 0。

经验上本跑 5/5 有 prior living HTF ZS。没有大量 `NO_HTF_ZS`。  
空间桶 5/5 = OUTSIDE。定义硬门已计量。

---

## Q2  zg/zd 稳定 ≠ 永远不变

不要把 H1/H5 的 identity 要求套回来。出生冻一组，后面只允许扩。

引擎没有 `enter_bi` 字段。`check_bi_div` 里的 `enter_bi = zs.bi_list[0].pre` 是 **LTF BSP 背驰**用的进入段，**不是** HTF Location 身份。禁止写进 HTF ledger。

HTF 出生冻结：

| 字段 | 源 |
|------|----|
| `start_bi` | `ChanBIZS.start_bi` = 三笔中的 bi1 |
| `enter_bis` | 出生三笔 `(bi1, bi2, bi3)`，zg/zd 只由它们算 |
| `zg` / `zd` | `get_zs_range(enter_bis)` |

后续允许：

| 字段 | 源 |
|------|----|
| `ZS_EXPAND` | 409–413 行：确认的 leave+back，back 与 `[zd,zg]` 重叠则并入 `bi_list` |
| `gg` / `dd` | `set_zs_bi_list` 随成员更新 |
| `zs_type` | `classify_zs()` |
| 末中枢 `is_sure` | 436–437 行跟 `bi_list[-1].is_sure`，会闪。**不是** Location 身份 |

扩员 **不重算** zg/zd。同一 `start_bi.start_time` 若 zg/zd 改写，或消失后换皮重生 → 该对象不能当 Location。不是去改引擎。

---

## Q3  空间桶（Phase 0）

合同里的 ZG附近 / ZD附近 **百分比阈值不冻**。

本阶段只报三档，用 `leave.end_klc` 的 `[low, high]` 对 `[zd, zg]`：

| 桶 | 几何 |
|----|------|
| `INSIDE` | `zd < low` 且 `high < zg`（严格在区间内，不碰边界） |
| `BOUNDARY_CONTACT` | K 线与 zg 或 zd 相交：`low <= zg <= high` 或 `low <= zd <= high` |
| `OUTSIDE` | `high < zd` 或 `low > zg` |

连续量 `pos = (low - zd) / (zg - zd)` 只记账，不参与分桶。  
主中枢规则仍按合同：多个仍有效对象时取 `pos` 离 `[0,1]` 最近，并列取更早 `T_HTF_ZS_VISIBLE`。

---

## Q4  B1 时 HTF ZS 是否仍有效

合同写「仍出现在列表」不够。

`cal_bi_zs_list_pure` **从不删除**旧中枢。历史 zs 会一直留在 `bi_zs_list`。  
「还在输出」几乎恒真，不能回答：

> B1 是落在活着的高周期结构空间，还是已经结束、只是残留的价格盒子？

本阶段拆开记，不合成一个分数：

| 字段 | 定义 |
|------|------|
| `zs_present_at_b1` | `T_LTF_B1` 的 HTF 前缀仍能按同一 identity 找到它 |
| `zs_living_at_b1` | 当时 `zs.next is None`（仍是最后一中枢，还可 `ZS_EXPAND`） |
| `zs_leftover_at_b1` | present 且已有后继中枢 |
| `zg_zd_unchanged` | 相对 visibility 未改写 |
| `ZS_valid_at_B1` | present ∧ zg/zd 未改写 ∧ **living** |

`NO_HTF_ZS`：没有 present 且未改写的对象。  
leftover 另列，不当成活空间，也不提前判死「残留盒子无意义」——那是 Phase 1+ 的事。

末中枢 `is_sure` 只报告，不进 `ZS_valid_at_B1`。

---

## Q5  完全不读 HTF BSP

HTF 路径零 BSP。

`TF_DF.init_TF_DF` 会算 `seg_list` / `zs_list`，但 **不会**调用 `find_all_bsp`（`bsp_list` 保持 `[]`）。  
仍禁止读取 `zs_list`、`big_zs_list`、`bsp_list`，禁止调用 `find_all_bsp` / `find_first_bsp` / `get_bsp_state`（后者走的是线段 `cal_bi_zs`，不是 pure）。

Ledger 出现下列键名即污染：

```
HTF_B1
HTF_B2
HTF_BSP
```

LTF 才允许 B1/B2 标签。字段名必须带 `LTF_` 前缀（`LTF_B1` / `T_LTF_B1`），避免和 HTF 混。

---

## Phase 0 报告字段（冻结名单，未填数）

每条候选 LTF B1 以后若授权记账，至少这些列：

```
T_HTF_ZS_VISIBLE
T_LTF_B1
Δt
ZS_birth_bar
B1_bar
ZS_valid_at_B1
zg_at_visibility
zd_at_visibility
zg_at_B1
zd_at_B1
```

附加（不进合同，只进本审计）：

```
zs_id                  start_bi.start_time
zs_present_at_b1
zs_living_at_b1
zs_leftover_at_b1
zg_zd_unchanged
ZS_EXPAND              bi_list 长度相对出生是否变长
spatial_bucket         INSIDE | BOUNDARY_CONTACT | OUTSIDE
pos
NO_HTF_ZS
```

这些列要能直接回答：B1 看到的 HTF 中枢，是不是在 B1 之前就已经作为稳定空间存在。  
SMOKE-60D-1H-15M 已填数：5 条 LTF B1_LOCK，全部 prior / living / OUTSIDE。

---

## Forbidden（本阶段）

- replay / 换 TF 比较 / OF / Entry / B2 完成率
- 给「附近」加百分比
- 把 leftover 中枢硬当成 living Location
- 把末中枢 `is_sure` 闪烁写成「中枢不存在」
- 把 LTF `check_bi_div.enter_bi` 写进 HTF 身份
- ledger 出现 `HTF_B1` / `HTF_B2` / `HTF_BSP`
- 改 `cal_bi_zs_list_pure` 来通过硬门

---

## 源码锚点

| 事实 | 位置 |
|------|------|
| 出生三笔 → zg/zd | `builders/zs.py` `cal_bi_zs_list_pure` 389–422 |
| ZS_EXPAND 不改 zg/zd | 同函数 403–413，`set_zg`/`set_zd` 只在出生调用 |
| 旧 zs 不删除 | 431 `bi_zs_list.append`；无 remove |
| 后继 | 427–429 `set_next` |
| 末中枢 is_sure 闪 | 436–437 |
| LTF B1/B2 | `builders/bsp.py` `find_all_bsp` 183–224 |
| BSP enter_bi（禁用到 HTF） | `check_bi_div` 228 |
