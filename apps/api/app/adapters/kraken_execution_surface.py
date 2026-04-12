"""
Kraken execution *surface* — architecture hook for Kraken CLI / API without live trading in this repo.

Default demo path: paper adapter in `execution_service`. This module produces:
- human + machine readable *draft* order payloads aligned with how a CLI wrapper would be called
- status metadata for the operator UI and challenge narrative

No subprocess / network I/O unless future explicit flags (not enabled in default .env).
"""

from dataclasses import dataclass
from typing import Any

from app.config import get_settings
from app.models import TradeIntent


@dataclass
class KrakenSurfaceStatus:
    active_execution_provider: str
    kraken_execution_enabled_flag: bool
    allow_real_orders: bool
    cli_command_stub: str
    routing_mode: str
    note: str


def get_surface_status() -> KrakenSurfaceStatus:
    s = get_settings()
    routing = "paper_simulator"
    if s.enable_kraken_execution and s.allow_real_orders:
        routing = "kraken_live_gated"
    elif s.kraken_cli_surface_enabled:
        routing = "kraken_cli_surface_ready"
    note = (
        "Demo default: fills use the in-process paper adapter. "
        "Kraken CLI path is a typed draft + interface for challenge alignment — "
        "flip ENABLE_KRAKEN_EXECUTION + ALLOW_REAL_ORDERS only when you intend real routing."
    )
    return KrakenSurfaceStatus(
        active_execution_provider=s.execution_provider,
        kraken_execution_enabled_flag=s.enable_kraken_execution,
        allow_real_orders=s.allow_real_orders,
        cli_command_stub=s.kraken_cli_command_stub,
        routing_mode=routing,
        note=note,
    )


def build_kraken_cli_order_draft(intent: TradeIntent, mark_price: float) -> dict[str, Any]:
    """Structured payload mirroring what a Kraken CLI layer would consume (no I/O)."""
    vol = round(intent.approved_size / mark_price, 8) if mark_price else 0.0
    return {
        "schema": "veritrade.kraken_cli_order_draft.v1",
        "pair": intent.asset,
        "side": intent.action.lower(),
        "ordertype": "market",
        "volume": vol,
        "approved_notional_usd": intent.approved_size,
        "intent_uuid": intent.intent_uuid,
        "policy_version": intent.policy_version,
        "risk_verdict": intent.risk_verdict,
        "cli_stub": get_settings().kraken_cli_command_stub,
        "disclaimer": "Draft only — not submitted by VeriTrade in paper mode.",
    }
