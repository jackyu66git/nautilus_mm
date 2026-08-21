# nautilus_mm — Research Freeze / Data Collection Phase

Freqtrade 保留缠论 / 中低频；**Maker / L2 / Fill 事件**迁到 NautilusTrader。

**研究对象：可验证的市场现象（不是策略）。**

```
Trading OS
  ├─ Market Intelligence (Market Pulse)     ← Stage5 才接（Quote Adjustment）
  ├─ Execution Reality Layer (本仓库)       ← Fill Alpha Dataset
  ├─ Freqtrade                              ← Chan / 中低频
  └─ NautilusTrader                         ← 事件驱动执行
```

## 冻结研究路径（禁止跳级）

```
Stage 0  Data Integrity
    ↓
Stage 1  Fill Alpha          ← 当前
    ↓
Stage 2  Maker Edge Report   ← 当前（决策门）
    ↓
Stage 3  Economic Simulation ← LOCKED until Edge PASS
    ↓
Stage 4  Quote Engine
    ↓
Stage 5  Market Regime Adaptation  (Market Pulse → Quote Adjustment)
```

| Stage | 目标 | 状态 |
|-------|------|------|
| **0** | WS/L2 可信：seq gap / latency / book_age | 探针已记 |
| **1** | Fill Alpha Dataset：真实成交 + 路径 | **进行中** |
| **2** | Maker Edge 决策门：PASS / FAIL / COLLECTING | **进行中** |
| **3** | 经济仿真：quote→fill→inventory→exit（partial/cancel/funding/fee） | **未解锁** |
| **4** | Quote Engine | 未开始 |
| **5** | Regime Adaptation | 未开始 |

原则：**先证明成交有优势，再谈账户收益，再设计报价。**  
禁止现在加：Quote Engine / AI / Market Pulse 交易信号 / 参数优化。

### 核心问题（交给 ~2000 真实 fills）

> 个人开发者在 BTC 永续上，通过被动流动性提供，是否能获得统计优势？  
> 若有：优势来自哪里？

可能结果：

| 情况 | 含义 | 下一步 |
|------|------|--------|
| **A** 全市场 PASS | 稳定被动流动性优势 | Symmetric MM |
| **B** 仅特定状态 PASS | 高波动 / 吸收 / 震荡等 | Event-driven LP（更可能） |
| **C** 全部 FAIL | 普通 Maker edge 不存在 | Cash Carry / Basis / Funding / 跨所 |

**最值得等待的不是 PASS，而是 Edge 来自哪里。** 第一份 FAIL 也是高价值结果。

### 防自我欺骗（已内建）

1. **Cluster-weighted** — 暴跌 50 笔 Bid ≠ 50 独立样本；同时看 fill-w 与 cluster-w，方向一致才可信  
2. **Matched Mid / Maker Alpha** — `MakerAlpha = Fill Outcome − Market Move`（剥离方向收益）  
3. **Adverse Selection** — 成交是否天然站在错误一侧；spread capture 挡不住毒流  

Stage 3（Economic Simulation）只在 Edge PASS 后做：partial fill、cancel latency、inventory limit、position aging、funding、fee tier → 真实账户收益分布。

## Maker Edge Report v0.1

```bash
./scripts/analyze.sh          # 默认 min-fills=2000
./scripts/analyze.sh 500      # 早期预览（仍为 COLLECTING）
```

报告结构：Data Integrity → Sample Independence → Fill Quality + Benchmark → Adverse Selection（`POSITIVE_EDGE` / `EDGE_AFTER_COST` / `NO_EDGE`）→ Path Attribution → State Stability → Decision。

## 快速开始

```bash
cd nautilus_mm
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # TESTNET key；代理默认 7897

./scripts/run_probe.sh           # 攒真实 fills
./scripts/analyze.sh 2000        # 决策门报告
```

探针只记 quote / fill / outcome。`market_state_snapshot` 预留为 null。

## 目录

```
nautilus_mm/
├── configs/
├── logs/maker_edge/          # Fill Alpha Dataset (jsonl)
├── scripts/
│   ├── run_probe.sh
│   ├── analyze.sh
│   ├── analyze_maker_edge.py
│   └── record_l2_ccxt.py
└── src/nautilus_mm/
    ├── recorder.py
    ├── health.py
    ├── book_utils.py
    ├── run_live.py
    └── strategies/maker_edge_probe.py
```

## 与 Freqtrade

| | Freqtrade | nautilus_mm |
|--|-----------|-------------|
| 用途 | 缠论 / 中低频 | Maker / L2 / Edge 验证 |
| 驱动 | K 线 | order book / fill 事件 |

## 安全

- 默认 `BINANCE_ENVIRONMENT=TESTNET`
- `ENABLE_TRADING=false` 可只订数据  
- **独立 `.venv`**，勿与 freqtrade 混装  

## 实验冻结（见 [FREEZE.md](FREEZE.md)）

**三不动：** Quote Logic / 成本模型 / PASS·COLLECTING·FAIL  

| ✅ 冻结期允许 | ❌ Gate 解锁前禁止 |
|-------------|-------------------|
| 数据字段 | 新交易规则 |
| 数据质量检查 | 新过滤条件 |
| 报告解释能力 | 新收益优化参数 |

Decision：`PASS` / `PARTIAL_PASS` / `COLLECTING` / `FAIL`  
观察窗：500 异常 · 2000 初步 · 10000 稳定性；**clusters > fills**。  
第一份报告先看分布（Fill / Cluster / Toxicity），再看 Decision。

## 服务器 Data Collection（zun_hk）

默认：

| | |
|--|--|
| Host | `jack@jackyu66.com` |
| Key | `~/Project/deploy/zun_hk/id_ed25519_hk` |
| Dir | `/www/Project/nautilus_mm` |
| Experiment | `MM_EDGE_EXP_001` |

```bash
./scripts/deploy_server.sh

ssh -i ~/Project/deploy/zun_hk/id_ed25519_hk jack@jackyu66.com
nano /www/Project/nautilus_mm/.env          # BINANCE_API_KEY / SECRET
systemctl --user start mm-edge-probe        # 用户级 systemd（无需 sudo）
journalctl --user -u mm-edge-probe -f

./scripts/probe_status.sh
./scripts/pull_report.sh 2000
```

本地短测：`USE_PROXY=true ./scripts/run_probe.sh`
