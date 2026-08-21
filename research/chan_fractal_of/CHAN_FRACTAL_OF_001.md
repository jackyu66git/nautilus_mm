# CHAN_FRACTAL_OF_001

```
CHAN_FRACTAL_OF_001
        │
        ▼
15m Fractal + 1m OF
        │
        ├── Phase A = PASS
        │
        ▼
Phase B = FAIL（仅 amplitude）
        B0 PASS · B1 Contrast PASS · B2 Confound FAIL · B3 NOT_RUN

HTF / SMC / classifier / OF threshold / Entry / 换 TF：仍 BLOCKED
B FAIL 之后才讨论尺度是不是问题。不拿 HTF/SMC 救。
```

研究问题：

> 在相同的分型事件上，OF 是否提供了超出价格振幅本身的额外信息？

判断顺序（固定，不可翻）：

```
1. 先看 OF 与 B1→B2 是否有差异
2. 再剥离 amplitude effect
3. 确认不是「更大波动 → 更容易 B1/B2」造成的假增量
4. 只有存在独立增量，才有资格继续研究空间层
5. 如果没有，微观 OF 链直接关闭
```

未授权：不做任何技术预研、不写 runner、不设计下一层。

---

## 树，不是漏斗

```
                 缠论
          空间 / 结构 / 分型
                  │
          ┌───────┴───────┐
         SMC             MACD
       盒内行为          动力效率
          └───────┬───────┘
                  ▼
                 OF
          当前成交是否支持
                  ▼
              B1 → B2     retrospective
```

不准做成：缠论出现 → SMC 满足 → MACD 满足 → OF 满足 → B1。  
同一分型事件上分别测量属性。本 Phase 只测 OF。

---

## 程序（每步都可失败）

```
Phase A   Fractal × OF     PASS
              │
              ▼
Phase B   OF × retrospective B1/B2，再剥离 amplitude
              │ 无独立增量 → 微观 OF 链关闭
              ▼ 有
以后才        才有资格谈空间层。现在不准设计
```

停在授权闸门。不开 HTF，不碰 SMC。

---

## Object（冻结）

分型 = 包含处理后的 KLC `check_fx`，不是 raw 1m K。

```
右K未完成（next.end_klu is None）→ 不分型
BOTTOM: 中间高低都低于左右
TOP:    中间高低都高于左右
身份:   中间 KLC.start_time
```

`BOTTOM2` / `TOP2`（`klc_fx_type`）不是本对象。

| 钟 | 定义 |
|----|------|
| `T_FX_FORMING` | 左、中 KLC 已走完，右 KLC **尚未** `end_klu`。分型未确认，但极值 K 已在 |
| `T_FX_VISIBLE` | 右 KLC 收盘 `next.end_time`。分型第一次在线确认 |
| 默认 TF | **第一研究尺度**：15m 因果闭合 KLC + 1m OF。可行，不是最佳周期。不比较其它 TF |

中间 K 的 low/high 是观察锚，不是确认钟。

---

## Phase A

### A1 因果

分型确认**之前**能看到哪些 OF？

窗口：左 ∪ 中 ∪（未完成的右，若已有已收盘 1m），且 `1m.time < T_FX_VISIBLE`。  
确认当根 `t == T_FX_VISIBLE` 的 OF 只进 A3 对照，不进 A1「形成前」特征。

禁止：确认之后的数据、B1/B2、T1/T2、未来成交、未来价格、HTF、SMC、MACD 层。

### A2 分布（先看信息量，不设阈值）

不准先写 `delta < -X` / `volume > X` / `absorption > X`。

先看：

- 底/顶分型的 OF 连续量分布
- 不同分型结构下的 OF（例如包含根数、中 KLC 宽度）
- 形成过程中的时间演化（窗口内 1m 路径，不是一个数）

先回答：OF 本身有没有足够的信息量？是不是所有分型的 OF 都挤在一起？

可记、不合成 score、不分类：

```
of_taker_buy
of_taker_sell
of_delta
of_volume
of_imbalance      (buy-sell)/(buy+sell)
```

absorption / exhaustion 只作事后描述名，A2 不冻成规则。

### A3 稳定性（forming → candidate → visible → confirmed）

同一 `fx_id`：

```
forming     中 KLC 已结束，右 K 尚未 end_klu
candidate   右 KLC 已出现但未完成
visible     check_fx 第一次成立（T_FX_VISIBLE）
confirmed   之后的前缀上该身份仍是同一 fx，未收回
```

不能出现：确认以后看到 OF 很漂亮 → 回头把这个分型定义成「强分型」。

forming / candidate / visible 的 OF 都只用 `t < T_FX_VISIBLE`。  
confirmed 只检查 fx 身份是否还在，**不加**确认后成交。

A3 FAIL：身份收回；或多数事件 forming 窗口空、visible 才有 OF（事后改写）。

---

## Hard gates（A 内顺序不可翻，前面 FAIL 后面 NOT_RUN）

| 门 | 通过 | 失败则 |
|----|------|--------|
| A1 Causality | 特征只用 `t < T_FX_VISIBLE`；零未来成交 | 停 |
| A1 Clock | `check_fx` 且右K `end_klu`；确认后身份不收回 | 停 |
| A2 Information | OF 分布不是单一团 / 不是全空 | 停 |
| A2 Same-root | 差异不是振幅/高低的同义改写 | 停 |
| A3 Identity | fx 不收回 | 停 |
| A3 No rewrite | 多数事件 forming 已有 OF；不用 visible 回头定义强弱 | 停 |

只有 **A1 PASS ∧ A2 PASS_CANDIDATE ∧ A3 PASS** 才有资格进入「OF 差异是否与 B1/B2 有关」。  
A PASS ≠ 可交易。

---

## Forbidden

- B1 / B2 / `find_all_bsp` / T1 / T2
- HTF 中枢、SMC、OB/FVG、MACD 独立层
- OF 预测 B2 / 下一根 K / Observation Open
- 为 A2 先设阈值、训练分类器、合成 strength score
- 用确认后 OF 重写 forming
- 改 `check_fx` 打出差异
- 开 HTF 实验、开 SMC ID
- Success / WR / PF / Entry / Nautilus

---

## Default combo（第一研究尺度，不是最佳 TF）

```
symbol:     BTCUSDT-PERP
structure:  15m 因果闭合 KLC 分型   ← 结构事件容器
OF:         1m taker_buy_base      ← 微观成交观察层
```

Phase A PASS ≠ 15m 是最佳分型周期。  
只证明：15m / 1m 作为研究尺度可行（因果干净、OF 有分布、身份未事后回写）。

Phase B 必须与 Phase A **完全同尺度**。现在不准加 5m/30m/1h 或改 OF 粒度。  
那会把问题改成「哪个 TF 最容易找到 OF edge」。

跨尺度只在 B 先证明 15m/1m 有独立 OF 增量之后才问：这种信息是否具有 scale invariance / scale sensitivity。不是为了挑 PF。

---

## SMOKE-60D-15M

Log: `logs/chan_fractal_of/CHAN_FRACTAL_OF_001/SMOKE-60D-15M/`

```
A1 PASS            n_fx=1957 bottom=978 top=979 leak=0
A2 PASS_CANDIDATE  std_delta=650.6 std_imb=0.1266
                   spearman(delta, signed_range)=0.415
                   spearman(imb, signed_range)=0.369
A3 PASS            retracted=0 rewrite=0/1957
decision           PASS
```

A PASS ≠ 可交易。≠ 已分出衰竭/吸收类型。≠ 可开 HTF/SMC。≠ OF 能预测买点。  
只表示：确认前 OF 存在、有分布差、不是振幅同义改写、forming 未被 visible 事后改写。

---

## Phase B（合同冻结，Replay BLOCKED）

问：

> 在 15m 分型事件上，1m OF 是否携带超出价格振幅本身的信息？

不问「OF 能不能预测 B2」。不准做成 classifier。不准换 TF。Phase B 与 Phase A 同尺度。

```
Fractal
   ↓
OF characterization     ← 特征只来自 t < T_FX_VISIBLE（Phase A 已冻）
   ↓
retrospective label     ← B1 / B2 只在最后 overlay
```

### 对象与标签（Truth only）

Phase A 的几何分型 **不是** 笔端点。B 必须把三列分开存，不准合成一个 score：

| 列 | 何时可知 | 进特征？ |
|----|----------|----------|
| `mid_range` | 分型几何 | 否。只作混杂对照 |
| OF forming 连续量 | `t < T_FX_VISIBLE` | 是。与 A 相同，不准加阈值 |
| `label_bi_endpoint` | 该 KLC 是否成为确认笔的 start/end | 否 |
| `label_B1` | `find_all_bsp` 的 B1 leave 端点是否就是该分型 | 否 |
| `label_B1_B2` | 同一 zs 上该 B1 后来有 B2 | 否 |

`label_B1_B2` 才是「B1→B2 样本」。其余是非样本。  
底分型对 B1，顶分型对 S1 对称；先报底。

B1 定义仍是 ALIGN：`leave` DOWN ∧ `check_bi_div` ∧ `zs.is_sure`。B2 同 `find_all_bsp`。禁止 `find_first_bsp`。标签用全样本事后结构，**不准**写回 OF。

### 必须防的坑

A2：OF 与振幅 Spearman ≈ 0.37–0.42。

因此 B 必须同时看到：

1. 两组的 `mid_range` 分布是否已经不同（B1/B2 是否只是更大波动）
2. OF 原始分布（不截断、不分类）
3. **在相近振幅桶内**，OF 是否仍有差

否则：`OF 强 → 波动大 → 更容易 B1/B2` 会被误当成独立解释力。

不准：OF threshold、strength score、classifier、用 B1 反推 OF。

### 门（授权后才跑）

| 门 | FAIL |
|----|------|
| B0 Leak | 特征用了 `t >= T_FX_VISIBLE` 或把 label 写进 OF |
| B1 Contrast | B1→B2 vs 非，OF 分布无结构差 |
| B2 Confound | 差能被 `mid_range` 单独解释（桶内消失） |
| B3 Bi-only | 差只存在于「几何分型 vs 笔端点」，与 B1/B2 无关 |

B1 Contrast PASS 且差只是 amplitude → FAIL，关闭微观链。  
全过 ≠ Entry。只表示：分型时的 OF 与事后 B1→B2 标签有不能被振幅还原的差。

裁决：独立 OF 增量才 PASS；无增量或仅 amplitude 都是 FAIL。FAIL 不准 HTF/SMC 救。

---

## SMOKE-60D-15M Phase B

Log: `logs/chan_fractal_of/CHAN_FRACTAL_OF_001/SMOKE-60D-15M/`

```
B0 PASS      leak=0  bottom=978  bi_ep=136  B1=5  B1_B2=5
B1 PASS      n_pos=5 n_neg=973
             cliff(OF delta)=-0.449  cliff(imb)=-0.159
             pos delta p50=-929   neg delta p50=-90
B2 FAIL      仅 amplitude
             cliff(mid_range)=+0.497
             pos range p50=175.5  neg range p50=116.7
             tertile: bin0 n_pos=0 · bin1 n_pos=2 SKIP · bin2 n_pos=3
             OF 只在最大振幅桶可测，不能排除「更大波动 → 更容易 B1/B2」
B3 NOT_RUN
decision     FAIL
```

B1 Contrast PASS 只说明两组 OF 有差。  
B2 说明这个差不能从振幅里拆出来：5 个 B1→B2 底分型明显更大，低/中振幅桶正样本不够匹配。

n_pos=5 本身也太薄，不能支撑「独立 OF 增量」。

FAIL ≠ 15m 不是可行尺度。Phase A 仍然成立。  
FAIL = 在 15m/1m 上，OF 没有超出 amplitude 的独立信息。

下一步只允许讨论：这是不是尺度问题。不准比较 TF 猎 edge，不准接 HTF/SMC。

---

## Forbidden（全程）

- 用 OF 预测 B2；classifier；threshold 猎金
- HTF 中枢、SMC、OB/FVG、Entry、Nautilus
- 开新假设层
- 现在比较 5m/30m/1h 或改 OF 粒度；把问题改成「哪个 TF 有 OF edge」
- Success / WR / PF
