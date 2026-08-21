# CHAN_FX_BI_TRADE_OF_001

```
Experiment:     CHAN_FX_BI_TRADE_OF_001
Status:         FAIL / NO_INCREMENT
                delta 复现。HHI / push 无结构差。
                当前 15m 结构上微观 OF 定级，停。
Type:           结构质量对照。不是 Alpha。不是 detector。不是 Phase 3 HHI
Structure:      与 CHAN_FX_BI_OF_001 同一批 15m 几何分型
Label:          同一 sure-bi 笔端点。retrospective。不准回写 OF
OF:             CHAN_TRADE_OF_001 forming aggTrades：delta / HHI / push
对照:           只换 OF 对象，不换结构，不换周期
B1 / B2:        FORBIDDEN
HTF / SMC / 5m / classifier / 交易阈值:  BLOCKED
```

问：

> 完整 OF 的新维度，能不能比单纯 delta 更好地描述
> 「这个分型最终成为确认笔端点」时的微观质量？

不问：OF 能不能预测 B2。不问 HHI→push 还是不是机制。

```
CHAN_FX_BI_OF_001                 CHAN_FX_BI_TRADE_OF_001
15m Fractal                       15m Fractal     （同一批）
    ↓                                 ↓
1m Kline taker-flow               forming aggTrades
    ↓                                 ↓
delta / imbalance                 delta / HHI / push
    ↓                                 ↓
PASS 中等排序，不是识别器          本 ID：有没有独立于 delta 的结构增量
```

```
15m 几何分型
      │
      ├── 普通分型
      │
      └── 最终成为确认笔端点
               │
               ▼
        forming 期间 aggTrades
        t < T_FX_VISIBLE
               │
        ├── delta     基线。已知有差异
        ├── HHI       是否有独立差异
        └── push      是否有独立差异
```

---

## 为什么现在开这个

`CHAN_TRADE_OF_001` Phase 2 = CONDITIONAL_MECHANISM。  
HHI→push 不是普适机制。不准再挖它的数学形式。

新维度仍然在：HHI 与 push 是 Kline 看不到的。  
职责冻结仍是：缠论找结构转折；OF 判断这个转折的微观质量。

所以把已确认的维度拿回结构对象，而不是继续解释条件相关。

成功标准很低：只问完整 OF 是否比 delta **多提供结构信息**。  
没有增量 → 当前 15m 结构上，微观 OF 研究价值定级，停。  
有增量 → 才有资格另开「确认端点之后的路径」；仍不自动开，仍不准 B1/B2。

---

## 对象锁

| 锁 | 值 |
|----|----|
| 结构 | 15m Fractal。forming 窗口与 `CHAN_FX_BI_OF_001` 相同 |
| 主对照人群 | **BOTTOM 分型**（与基线同一 978 / 136，数字必须对上） |
| 标签 | `label_bi_endpoint` 只来自已完成 `EVENTS.jsonl`。不准重跑 BSP |
| OF | 只读已完成 `PHASE_0_EVENTS.jsonl`。不准重扫成交、不准读 `T_FX_VISIBLE` 之后 |
| 特征 | `kline_delta` / `hhi` / `push`。speed 已丢弃，不准回来 |
| 混杂 | `mid_range`、`|delta|`。不准当特征猎金 |
| 拼接 | 按 `fx_id` 1:1。丢事件 = CLOCK |

不准同时改周期。不准把 TOP 拿来救 BOTTOM 的 FAIL。

---

## 门（顺序不可翻）

门槛沿用 `CHAN_FX_BI_OF_001`：`CLIFF_NEGLIGIBLE=0.147`，`MIN_GROUP=50`，振幅 / `|delta|` 各 3 桶，桶内 `n_bi≥15`、`n_ord≥30`。不准另设交易阈值。

| 门 | 只问 | FAIL 则 |
|----|------|---------|
| C0 Join/Size | `fx_id` 与两份 ledger 1:1；BOTTOM ordinary / bi 两边都够数，且人数与基线一致 | 停。对象不是同一批 |
| C1 Identity | leak=0；fx 不收回；只标 sure 笔；ledger 无 B1/B2；无 absorption / classifier 字段 | 停 |
| C2 Contrast | **delta 必须复现**有结构差。然后：HHI 或 push 的 \|Cliff δ\| ≥ 0.147 | delta 复现失败 → CLOCK。HHI 与 push 都无差 → **NO_INCREMENT** |
| C3 Confound | 通过 C2 的新维度，差不能被 amplitude 单独解释，也不能被 \|delta\| 单独解释；不能只在最大桶可测 | 仅 amplitude 或仅 delta 的副产物 → **NO_INCREMENT** |

C2 里 delta 是基线，不是新发现。  
C2 PASS 只表示 HHI 或 push **看起来**有组间差。  
C3 PASS 才叫独立于 delta / amplitude 的结构信息。

没有「组合分数」。不准加权、不准 logistic、不准猎分位。组合问句 = C3。

---

## 三个出口

| 结果 | 含义 |
|------|------|
| PASS / INDEPENDENT_STRUCTURE | HHI 或 push 对笔端点有独立于 delta 与 amplitude 的结构差。仍 ≠ detector。仍 ≠ Edge。不准自动开经济链或 B1/B2 |
| FAIL / NO_INCREMENT | 完整 OF 相对 delta 没有多提供结构信息。当前 15m 结构上微观 OF 定级，停。不准 Phase 3 HHI，不准换 TF 救，不准接 B1/B2 |
| FAIL / CLOCK | 拼接 / 泄漏 / 人数对不上。不准解释成 OF 失败 |

PASS ≠ 可交易。≠ OF 能识别笔端点。≠ 已证明端点后路径有经济意义。

---

## 清单（不是门）

与 `CHAN_FX_BI_OF_001` 同一口径记录，方便对照，**不参与 PASS/FAIL**：

- 几何分型 → 笔端点基准率（应仍 ≈ 13.9%）
- delta Top-`n_bi` 命中（基线约 27.9%；方向冻结：更空更像底端点）
- HHI / push 按 C2 符号的 Top-`n_bi` 命中与 AUC
- 各特征 Cliff δ 与 p50

不准把清单里的命中率改写成 detector 阈值。

---

## Forbidden

- 重开 `CHAN_TRADE_OF_001` Phase 3 / 继续救 HHI→push
- B1/B2、HTF、SMC、换 5m、L2
- absorption / exhaustion 命名
- classifier、组合分、交易阈值、回测、WR / PF / Entry
- 用 TOP 或换人群翻案
- 用确认后成交重写 forming

```
CHAN_FX_BI_TRADE_OF_001 = FAIL / NO_INCREMENT
≠ NEW_EDGE
不准 B1/B2 HTF SMC 5m Phase 3 HHI
```

Log: `logs/chan_fx_bi_trade_of/CHAN_FX_BI_TRADE_OF_001/SMOKE-60D-15M/`

---

## SMOKE-60D-15M

同一 1957 个 15m forming 事件。按 `fx_id` 拼接 `CHAN_FX_BI_OF_001` 标签与 `CHAN_TRADE_OF_001` aggTrades 特征。未重扫成交。未重跑 BSP。

| 门 | 结果 |
|----|------|
| C0 | PASS join 1:1 bottom=978 ordinary=842 bi=136（与基线一致） |
| C1 | PASS leak=0 retracted=0 |
| C2 | **FAIL** delta Cliff δ=**−0.316**（复现）。HHI **−0.104**、push **−0.125**，均 < 0.147 |
| C3 | NOT_RUN |

delta 基线原样复现：

| 指标 | CHAN_FX_BI_OF_001 | 本 ID |
|------|-------------------|-------|
| Cliff δ | −0.316 | −0.316 |
| bi / ordinary p50 | −256 / −72 | −256 / −72 |
| Top-136 命中 | 38 / 136 = 27.9% | 38 / 136 = 27.9% |
| AUC | 0.66 | 0.658 |

新维度没有多提供结构信息：

| 特征 | Cliff δ | Top-136 命中 | 对照随机 13.9% |
|------|---------|--------------|----------------|
| delta | −0.316 | 27.9% | 已知 |
| HHI | −0.104 | 18.4% | 未过门槛 |
| push | −0.125 | 16.2% | 未过门槛 |

准确说法：aggTrades 的 HHI / push 是 Kline 看不到的维度（`CHAN_TRADE_OF_001`），但它们**不能**比单纯 delta 更好地描述「这个 15m 分型最终是否成为确认笔端点」。C3 未跑，因为组间差本身就不成立，无需再问是不是 amplitude 副产物。

```
CHAN_FX_BI_TRADE_OF_001 / FAIL / NO_INCREMENT
当前 15m 结构上，微观 OF 研究价值定级：
  有新维度，没有附着到缠论笔端点的独立结构增量。
停。不准 Phase 3 HHI。不准换 TF 救。不准接 B1/B2。不准开端点后经济链。
```
