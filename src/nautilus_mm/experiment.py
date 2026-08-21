"""
实验身份绑定 — Research Freeze / Data Collection

每条 jsonl 与每份 Maker Edge Report 必须绑定同一 Experiment ID，
避免 v2/v3 混淆「哪个实验验证出了什么」。

冻结字段（运行期不可为「结果好看」而改）：
  quote / fee / exchange / probe version
"""

from __future__ import annotations

import os
from typing import Any


# 默认实验身份（可用环境变量覆盖 ID，其余保持 frozen 语义）
DEFAULT_EXPERIMENT_ID = "MM_EDGE_EXP_001"
DEFAULT_PROBE_VERSION = "probe_v0.1"

EXP_002_ID = "MM_EDGE_EXP_002"
EXP_002_PROBE_VERSION = "event_state_v0.1"


def load_experiment_meta() -> dict[str, Any]:
    """从环境变量加载实验元数据；冻结维度固定为 frozen。"""
    exp_id = os.getenv("EXPERIMENT_ID", DEFAULT_EXPERIMENT_ID)
    probe_version = os.getenv("PROBE_VERSION", DEFAULT_PROBE_VERSION)
    if exp_id == EXP_002_ID:
        phase = "Event-State Observability / Data Collection"
        experiment_type = "Event-State Observability Probe"
    else:
        phase = "Research Freeze / Data Collection"
        experiment_type = "Maker Edge Phenomenon Probe"
    return {
        "experiment_id": exp_id,
        "probe_version": probe_version,
        "experiment_type": experiment_type,
        "quote_assumption": "frozen",
        "fee_model": "frozen",
        "exchange_assumption": "frozen",
        "exchange": os.getenv("EXCHANGE_NAME", "binance_usdm"),
        "environment": os.getenv("BINANCE_ENVIRONMENT", "TESTNET").upper(),
        "symbol": os.getenv("SYMBOL", "BTCUSDT-PERP"),
        "phase": phase,
        "depends_on": "MM_EDGE_EXP_001" if exp_id == EXP_002_ID else None,
    }


def stamp_event(event: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """给单条事件打上实验身份（不覆盖已有显式字段）。"""
    m = meta or load_experiment_meta()
    event.setdefault("experiment_id", m["experiment_id"])
    event.setdefault("probe_version", m["probe_version"])
    event.setdefault("experiment", {
        "quote": m["quote_assumption"],
        "fee": m["fee_model"],
        "exchange": m["exchange_assumption"],
        "venue": m["exchange"],
        "environment": m["environment"],
        "symbol": m["symbol"],
    })
    return event
