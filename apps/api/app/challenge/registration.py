"""ERC-8004 draft-shaped agent registration file (EIP-8004 § Agent URI and Agent Registration File)."""

from __future__ import annotations

import json
import copy
from pathlib import Path

from app.config import Settings


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _base_registration() -> dict:
    path = _repo_root() / "spec-alignment" / "agent-registration.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_agent_registration(settings: Settings) -> dict:
    """Merge repo template with runtime URLs from settings (truthful endpoints)."""
    doc = copy.deepcopy(_base_registration())
    web = settings.veritrade_web_base_url.rstrip("/")
    api = settings.veritrade_api_base_url.rstrip("/")
    doc["image"] = f"{web}/veritrade-agent.svg"
    doc["services"] = [
        {"name": "web", "endpoint": f"{web}/", "version": "1.0.0"},
        {"name": "http", "endpoint": f"{api}/docs", "version": "openapi"},
        {"name": "http", "endpoint": f"{api}/challenge/context", "version": "1.0.0"},
        {"name": "http", "endpoint": f"{api}/challenge/agent-registration", "version": "1.0.0"},
    ]
    rid = (settings.erc8004_identity_registry_address or "").strip()
    aid = (settings.erc8004_onchain_agent_id or "").strip()
    if rid and aid:
        entry: dict = {"agentRegistry": rid, "agentId": aid}
        uri_eff = agent_uri_effective(settings)
        if uri_eff:
            entry["agentURI"] = uri_eff
        doc["registrations"] = [entry]
    else:
        doc["registrations"] = []

    wallet = (settings.veritrade_agent_wallet_placeholder or "").strip()
    if wallet:
        # Optional draft-adjacent field: not cryptographically proven here; may mirror local `setMetadata("agentWallet",…)`.
        doc["agentWallet"] = wallet

    return doc


def agent_registration_static_url(settings: Settings) -> str:
    return f"{settings.veritrade_web_base_url.rstrip('/')}/.well-known/agent-registration.json"


def agent_uri_effective(settings: Settings) -> str | None:
    stub = (settings.erc8004_agent_uri_stub or "").strip()
    if stub:
        return stub
    return agent_registration_static_url(settings)
