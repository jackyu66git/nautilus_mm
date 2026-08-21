#!/usr/bin/env python3
"""
Launch Event-State Observability Probe (MM_EDGE_EXP_002)

Data collection only — NO trading, NO strategy, NO Stage 3 unlock.

Environment:
  EXPERIMENT_ID=MM_EDGE_EXP_002
  PROBE_VERSION=event_state_v0.1
  ENABLE_TRADING=false   (hard-enforced; any true value is ignored)

Usage:
  cd nautilus_mm
  source .venv/bin/activate
  export PYTHONPATH=src
  python -m nautilus_mm.run_event_state
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

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
from nautilus_mm.strategies.event_state_probe import EventStateProbe
from nautilus_mm.strategies.event_state_probe import EventStateProbeConfig


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y")


def _resolve_environment() -> BinanceEnvironment:
    raw = os.getenv("BINANCE_ENVIRONMENT", "TESTNET")
    env_name = raw.strip().upper()
    if env_name not in ("TESTNET", "LIVE"):
        print(f"ERROR: BINANCE_ENVIRONMENT must be TESTNET or LIVE, got {raw!r}")
        sys.exit(1)
    if env_name == "LIVE" and not _env_bool("I_UNDERSTAND_LIVE", False):
        print("ERROR: LIVE blocked for EXP_002 unless I_UNDERSTAND_LIVE=yes")
        sys.exit(1)
    return BinanceEnvironment.LIVE if env_name == "LIVE" else BinanceEnvironment.TESTNET


def main() -> None:
    # Layer 2: runner hard-forces trading off even if .env / systemd is wrong
    if _env_bool("ENABLE_TRADING", False):
        print(
            "WARNING: ENABLE_TRADING=true ignored — MM_EDGE_EXP_002 is observability-only"
        )
    os.environ["ENABLE_TRADING"] = "false"
    os.environ["EXPERIMENT_ID"] = "MM_EDGE_EXP_002"
    os.environ.setdefault("PROBE_VERSION", "event_state_v0.1")

    exp_id = os.getenv("EXPERIMENT_ID", "MM_EDGE_EXP_002")
    if exp_id != "MM_EDGE_EXP_002":
        print(
            f"WARNING: EXPERIMENT_ID={exp_id!r} — expected MM_EDGE_EXP_002 for this runner"
        )

    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    environment = _resolve_environment()
    symbol = os.getenv("SYMBOL", "BTCUSDT-PERP")
    instrument_id = InstrumentId.from_str(f"{symbol}.{BINANCE}")
    log_dir = os.getenv("EVENT_STATE_LOG_DIR", str(_ROOT / "logs" / "event_state"))

    if not api_key or not api_secret:
        print("ERROR: set BINANCE_API_KEY / BINANCE_API_SECRET in nautilus_mm/.env")
        sys.exit(1)

    config_node = TradingNodeConfig(
        trader_id=TraderId("EVENT-STATE-002"),
        logging=LoggingConfig(log_level="INFO", log_colors=True, use_pyo3=True),
        data_engine=LiveDataEngineConfig(external_clients=[ClientId(BINANCE)]),
        exec_engine=LiveExecEngineConfig(
            reconciliation=False,
            open_check_interval_secs=0.0,
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
    strat_config = EventStateProbeConfig(
        instrument_id=instrument_id,
        book_depth=int(os.getenv("BOOK_DEPTH", "10")),
        log_dir=log_dir,
        prefill_window_sec=float(os.getenv("PREFILL_WINDOW_SEC", "5.0")),
        prefill_margin_sec=float(os.getenv("PREFILL_MARGIN_SEC", "0.25")),
        large_trade_qty=float(os.getenv("LARGE_TRADE_QTY", "0.1")),
        log_every_book_delta=_env_bool("LOG_EVERY_BOOK_DELTA", True),
    )
    node.trader.add_strategy(EventStateProbe(config=strat_config))
    node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
    node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
    node.build()

    exp = load_experiment_meta()
    print(
        f"[event_state] Experiment={exp['experiment_id']} {exp['probe_version']} | "
        f"type=Event-State Observability | trading=NO | {symbol} env={environment} | "
        f"run={os.getenv('LEDGER_RUN_ID', 'EXP-002-RUN-UNSET')} | log={log_dir}"
    )
    try:
        node.run()
    finally:
        node.dispose()


if __name__ == "__main__":
    main()
