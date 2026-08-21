#!/usr/bin/env python3
"""
启动 Nautilus TradingNode + MakerEdgeProbe（Binance USDT-M）

环境变量（或 .env）：
  BINANCE_API_KEY
  BINANCE_API_SECRET
  BINANCE_ENVIRONMENT=TESTNET|LIVE   (仅允许这两个值；默认 TESTNET)
  I_UNDERSTAND_LIVE=yes              (LIVE 必填)
  ENABLE_TRADING=false               (默认关闭；显式 true 才挂单)
  HTTP_PROXY / HTTPS_PROXY           (可选)

用法：
  cd nautilus_mm
  source .venv/bin/activate
  export PYTHONPATH=src
  python -m nautilus_mm.run_live
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

# ensure src on path when run as script
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

load_dotenv(_ROOT / ".env")

from nautilus_trader.adapters.binance import BINANCE
from nautilus_trader.adapters.binance import BinanceAccountType
from nautilus_trader.adapters.binance import BinanceDataClientConfig
from nautilus_trader.adapters.binance import BinanceExecClientConfig
from nautilus_trader.adapters.binance import BinanceInstrumentProviderConfig
from nautilus_trader.adapters.binance import BinanceLiveDataClientFactory
from nautilus_trader.adapters.binance import BinanceLiveExecClientFactory
from nautilus_trader.adapters.binance.common.enums import BinanceEnvironment
from nautilus_trader.config import LiveDataEngineConfig
from nautilus_trader.config import LiveExecEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId

from nautilus_mm.experiment import load_experiment_meta
from nautilus_mm.strategies.maker_edge_probe import MakerEdgeProbe
from nautilus_mm.strategies.maker_edge_probe import MakerEdgeProbeConfig


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y")


def _resolve_environment() -> BinanceEnvironment:
    raw = os.getenv("BINANCE_ENVIRONMENT", "TESTNET")
    env_name = raw.strip().upper()
    if env_name not in ("TESTNET", "LIVE"):
        print(
            f"ERROR: BINANCE_ENVIRONMENT must be exactly TESTNET or LIVE, got {raw!r}"
        )
        sys.exit(1)
    if env_name == "LIVE":
        if not _env_bool("I_UNDERSTAND_LIVE", False):
            print(
                "ERROR: LIVE trading blocked. Set I_UNDERSTAND_LIVE=yes "
                "only after you accept real-money risk."
            )
            sys.exit(1)
        return BinanceEnvironment.LIVE
    return BinanceEnvironment.TESTNET


def main() -> None:
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    environment = _resolve_environment()

    symbol = os.getenv("SYMBOL", "BTCUSDT-PERP")
    instrument_id = InstrumentId.from_str(f"{symbol}.{BINANCE}")
    order_qty = Decimal(os.getenv("ORDER_QTY", "0.001"))
    enable_trading = _env_bool("ENABLE_TRADING", False)
    max_abs_inventory = Decimal(os.getenv("MAX_ABS_INVENTORY", "0.005"))
    quote_ttl_secs = float(os.getenv("QUOTE_TTL_SECS", "30"))
    log_dir = os.getenv("MAKER_EDGE_LOG_DIR", str(_ROOT / "logs" / "maker_edge"))

    # 代理：Nautilus/httpx 会读 HTTP(S)_PROXY；这里仅提示
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or ""
    if proxy:
        print(f"[nautilus_mm] using proxy: {proxy}")

    if not api_key or not api_secret:
        print("ERROR: set BINANCE_API_KEY / BINANCE_API_SECRET in nautilus_mm/.env")
        print("For TESTNET keys: https://testnet.binancefuture.com/")
        sys.exit(1)

    config_node = TradingNodeConfig(
        trader_id=TraderId("MAKER-EDGE-001"),
        logging=LoggingConfig(log_level="INFO", log_colors=True, use_pyo3=True),
        data_engine=LiveDataEngineConfig(external_clients=[ClientId(BINANCE)]),
        exec_engine=LiveExecEngineConfig(
            reconciliation=True,
            open_check_interval_secs=5.0,
            graceful_shutdown_on_exception=True,
        ),
        data_clients={
            BINANCE: BinanceDataClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                account_type=BinanceAccountType.USDT_FUTURES,
                environment=environment,
                instrument_provider=BinanceInstrumentProviderConfig(
                    load_ids=frozenset([instrument_id]),
                ),
            ),
        },
        exec_clients={
            BINANCE: BinanceExecClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                account_type=BinanceAccountType.USDT_FUTURES,
                environment=environment,
                instrument_provider=BinanceInstrumentProviderConfig(
                    load_ids=frozenset([instrument_id]),
                ),
                max_retries=3,
            ),
        },
        timeout_connection=30.0,
        timeout_reconciliation=10.0,
        timeout_portfolio=10.0,
        timeout_disconnection=10.0,
        timeout_post_stop=5.0,
    )

    node = TradingNode(config=config_node)

    strat_config = MakerEdgeProbeConfig(
        instrument_id=instrument_id,
        order_qty=order_qty,
        book_depth=10,
        quote_offset_ticks=1,
        max_quotes=1,
        quote_ttl_secs=quote_ttl_secs,
        cooldown_secs=float(os.getenv("COOLDOWN_SECS", "60")),
        book_sample_secs=2.0,
        log_dir=log_dir,
        obi_enter=float(os.getenv("OBI_ENTER", "0.25")),
        enable_trading=enable_trading,
        max_abs_inventory=max_abs_inventory,
    )
    strategy = MakerEdgeProbe(config=strat_config)
    node.trader.add_strategy(strategy)

    node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
    node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
    node.build()

    exp = load_experiment_meta()
    print(
        f"[nautilus_mm] Experiment={exp['experiment_id']} {exp['probe_version']} "
        f"quote/fee/exchange=frozen | {symbol} env={environment} "
        f"trading={enable_trading} ttl={quote_ttl_secs}s max_inv={max_abs_inventory} "
        f"log={log_dir}"
    )
    try:
        node.run()
    finally:
        node.dispose()


if __name__ == "__main__":
    main()
