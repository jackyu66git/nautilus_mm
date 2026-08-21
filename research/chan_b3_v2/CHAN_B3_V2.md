# CHAN_B3_V2

```
Track:     Structure-only TP 对照。接 Exit Census A_SMALLER_TARGET
Phase:     唯一变量 = TP。不是 OOS。不是 Economic PASS。无手续费
Input:     冻结 20 个 15m B3/S3。Entry/Stop/Time/窗口与 V1 相同
```

只比 0.5R / 0.75R / 1.0R。不准 0.25R、EMA、OF、ATR、新 Entry/Stop/Time。
B3 / S3 分记。不合桶当 Alpha。不按 PF 选参。
V1 −0.58R 不是 Economic FAIL。V2_100 必须复现 V1：WIN=4 LOSS=4 TIME=12。

WIN 记 +TP（0.5 / 0.75 / 1.0）。LOSS 仍是 −1R（Stop=盒沿）。TIME_EXIT 按 24h close 计 R。

## 预注册闸门

相对 V1 TIME=12/20=0.60，avg R=−0.029。

```
TIME 明显下降     time_share ≤ 0.40（降 ≥20pp）
期望改善         avg R > 0  或  avg R ≥ V1 + 0.10
无方向冲突       不是「一家 >+0.10 且另一家 <−0.10」
非单笔撑起       去掉 |R| 最大一笔后，期望条件仍成立
```

- **PASS**：至少一档满足四条。冻结 **通过档里最小的 TP**（几何优先，不是最高 PF）。OOS 另授权。
- **HOLD**：三档差不多，或差异靠几笔，或 B3/S3 分裂。等自然样本。
- **FAIL**：0.5R 到达高，但扣 Stop 后仍无经济价值（avg R≤0 且未明显好于 V1）。停 TP 线，才允许回头看 Entry。不准加指标。

## 冻结结果

`HOLD / FAMILY_SPLIT`。freeze=无。V2_100 复现 V1：WIN=4 LOSS=4 TIME=12。

| 档 | WIN | LOSS | TIME | time% | hit | avg R | B3 avg R | S3 avg R | gate |
|----|-----|------|------|-------|-----|-------|----------|----------|------|
| 0.5R | 11 | 3 | 6 | 0.30 | 0.55 | +0.091 | +0.226 | −0.112 | TIME↓ 期望+ 但 B3/S3 冲突 |
| 0.75R | 6 | 4 | 10 | 0.50 | 0.30 | −0.005 | +0.057 | −0.097 | TIME 未降够 |
| 1.0R | 4 | 4 | 12 | 0.60 | 0.20 | −0.029 | −0.026 | −0.034 | V1 复现 |

不是 FAIL：0.5R 合样本 avg R>0，TIME 12→6。
不是冻结：S3 n=8 avg R=−0.11，触发预注册方向冲突。
不准改成只做 B3 来绕开 HOLD。不准加 EMA/OF。不准同一 20 笔当 OOS。

## 0.5R = Candidate（挂起，不是 FAIL）

```
B3/S3 Structure
       │
       ▼
Exit Geometry → 0.5R Candidate
       │
       ├── B3 目前支持（+0.226R，n=12）
       └── S3 目前不支持（−0.112R，n=8）
               │
               ▼
          FAMILY_SPLIT → HOLD
               │
               ▼
          等自然 S3
```

主交易候选继续挂着。不再开结构研究。EMA52 / OF / Trend Age 全冻。
不准用指标救 S3。不准把系统改成只做三买。

## 等待期锁定合同

等不是停工，是合同：让市场自然再产生至少 8 个 S3，避免挑选观察窗。G-R 已结束（NO_TAIL），不另开 Risk Distance Gate。

| 槽 | 锁定 |
|----|------|
| Entry | 确认后下一根 15m 开盘 |
| Stop | 中枢反向盒沿 |
| TP | 0.5R |
| Time Exit | 24h |
| 1R 定义 | Entry 到结构 Stop 的距离，不是 ATR |
| 方向 | B3 与 S3 都做。不允许只做 B3 |
| EMA52 / OF / Trend Age | 冻结 |
| 其他 TP | 不扫 |
| n_S3 < 16 | 不偷看、不复检 |

下一格见 [`CHAN_TO_LIVE.md`](../CHAN_TO_LIVE.md)。G-R = NO_TAIL。G0b = N/A。
到 n_S3 = 16 只跑一次 `CHAN_B3_V2_RECHECK`。过闸 → TP_CANDIDATE → OOS 另授权。不过闸 → 按预注册停，不为过闸调参。不准 Cap Stop。


## 复检时钟（预注册，未到不准跑）

ID：`CHAN_B3_V2_RECHECK`。合同不变：0.5R · T1 open · 盒沿 Stop · 24h。
定义仍是冻结三买检测。只允许时间向前长出新的 15m B3/S3。不准改 001 结构定义窗来凑数。
**不到 n_S3 ≥ 16 不准复检**（当前 8，至少再等 8 个自然 S3）。不准在 9…15 上偷看。

复检只看 0.5R，不再扫 0.75/1.0 网格。

## 升级条件（同时满足才 PASS / TP_CANDIDATE）

1. B3 avg R > 0
2. S3 avg R > −0.10（不再明显负；不要求与 B3 一样强）
3. 合样本 avg R > 0
4. 去掉 |R| 最大一笔后，合样本期望条件仍成立
5. 无新变量（无 EMA / OF / ATR / 新 Entry / 新 Stop / 新 Time）

成立 → 冻结 0.5R → OOS / Economic 另授权。
仍 FAMILY_SPLIT → 那时才允许问 B3/S3 是否结构不对称。现在不许问。

