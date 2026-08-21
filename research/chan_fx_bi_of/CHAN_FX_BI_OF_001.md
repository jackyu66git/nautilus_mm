# CHAN_FX_BI_OF_001

```
Experiment:     CHAN_FX_BI_OF_001
decision:       PASS
C0/C1/C2/C3:    PASS
B1 / B2:        FORBIDDEN 未开
HTF / SMC / 换 TF:  BLOCKED
```

问：

> 同样的 1m OF，在所有 15m 分型与「最终成为笔端点的分型」之间，是否存在结构性差异？

```
                    15m 分型
                       │
             ┌─────────┴─────────┐
             │                   │
        普通分型             笔端点分型
             │                   │
             └─────────┬─────────┘
                       ▼
                    1m OF
```

笔端点 = 普通分型的 **retrospective** 标签。  
OF 只用 `t < T_FX_VISIBLE`。不准用成笔回写 OF。

不是把分型对象换成笔端点。是对照：OF 识别的是局部反转，还是缠论结构端点。

---

## 为什么开这个，而不是 Phase B2 / 换 TF

Phase B：978 底分型里只有 5 个 B1→B2，标签太稀。  
本 ID 先问结构质量，不碰买点。比换 TF 干净。

---

## 字段

| 字段 | 来源 | 进 OF 特征？ |
|------|------|----------------|
| `T_FX_VISIBLE` | 在线 | 钟 |
| OF raw | `t < T_FX_VISIBLE` | 是 |
| `mid_range` | 分型几何 | 否。混杂对照 |
| `label_bi_endpoint` | 事后 sure 笔 start/end | 否 |
| B1/B2 | — | 本 ID 禁止出现 |

---

## 门（顺序不可翻）

| 门 | 问 | FAIL |
|----|----|------|
| C0 Size | 普通 vs 笔端点，底分型两边都够数 | 停。对象仍太稀 |
| C1 Identity | leak=0；fx 不收回；只标 sure 笔；ledger 无 B1/B2；OF 不经 label 回写 | 停 |
| C2 Contrast | 两组 OF 分布有结构差 | OF 不识别缠论端点质量 → 关闭本微观链 |
| C3 Confound | 差不能被 amplitude 单独解释；不能只在最大振幅桶可测 | 仅 amplitude → 同样视为无独立 OF 增量 |

C2 PASS ∧ C3 PASS → 才有资格再问：这种对笔端点的 OF 描述是否对 B1/B2 有增量。  
本 ID 到此为止，不自动开 B1/B2。

C2 FAIL 或 C3 FAIL → 关闭 OF 微观链。不准换 TF 救，不准 HTF/SMC 救。

---

## SMOKE-60D-15M

Log: `logs/chan_fx_bi_of/CHAN_FX_BI_OF_001/SMOKE-60D-15M/`

```
C0 PASS   bottom=978  ordinary=842  bi_endpoint=136  unmatched_ep=0
C1 PASS   leak=0 retracted=0 forming_empty=0  sure_bi=271  B1/B2 absent
C2 PASS   cliff(delta)=-0.316  cliff(imb)=-0.208
          bi delta p50=-256   ordinary p50=-72
C3 PASS   cliff(mid_range)=+0.268
          bin0 n_bi=29  cliff_delta=-0.113  (negligible)
          bin1 n_bi=39  cliff_delta=-0.330  (survives, not max bin)
          bin2 n_bi=68  cliff_delta=-0.337
decision  PASS
```

PASS ≠ 可交易。≠ OF 能识别笔端点。≠ 已证明 OF 能预测 B1/B2。

准确说法：OF 对「一个分型最终是否成为笔端点」具有**中等排序信息**。

| 指标 | 结果 | 解释 |
|------|------|------|
| 几何分型 → 笔端点 | 136 / 978 = 13.9% | 结构基准率 |
| OF delta 排序 Top 136 命中 | 38 / 136 = 27.9% | 约 2.0× 随机 |
| OF imbalance Top 136 命中 | 21 / 136 = 15.4% | 约 1.1× 随机 |
| delta AUC | 0.66 | 中等排序 |
| imbalance AUC | 0.60 | 较弱 |
| delta Cliff’s δ | −0.316 | 与 AUC 一致 |

没有 `delta < −X → 笔端点`。72.1% 的 Top-136 仍不是笔端点。OF **不是**端点 detector。

关系是连续的：OF 更空 → 成笔概率上升 → 不是确定性。

下一枪不是 B1/B2，也不是识别率。见 `CHAN_BI_OF_STRATA_001`：在确认笔端点上按 OF 分桶看经济差异。Replay 另授权。
