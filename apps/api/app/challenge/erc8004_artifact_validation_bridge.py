"""
Optional bridge: after an artifact is written, emit a validationRequest on-chain (local/testnet).

**Default: disabled.** Enable only with explicit env (see Settings). Never blocks the trading loop.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.challenge.erc8004_validation import Erc8004ValidationRequestPayload, validation_request_hash_from_canonical_payload
from app.config import Settings

log = logging.getLogger(__name__)


def _selector(sig: str) -> bytes:
    from eth_utils import keccak

    return keccak(text=sig)[:4]


def maybe_emit_validation_request_for_artifact(
    settings: Settings,
    *,
    artifact_type: str,
    artifact_id: int,
    related_id: str,
    payload: dict[str, Any],
    artifact_json_path: Path,
) -> dict[str, Any] | None:
    """
    Best-effort on-chain validationRequest. Returns a small status dict when attempted, else None.

    Swallows errors — callers must not depend on success for correctness of artifact persistence.
    """
    if not settings.erc8004_artifact_validation_emit_enabled:
        return None

    types = {t.strip().lower() for t in settings.erc8004_artifact_validation_trigger_types.split(",") if t.strip()}
    if artifact_type.lower() not in types:
        return None

    rpc = (settings.erc8004_rpc_url or "").strip()
    pk = (settings.erc8004_artifact_validation_private_key or "").strip()
    reg = (settings.erc8004_artifact_validation_registry_address or settings.erc8004_validation_registry_address or "").strip()
    val = (settings.erc8004_artifact_validation_validator_address or "").strip()
    aid = (settings.erc8004_onchain_agent_id or "").strip()

    if not rpc or not pk or not reg or not val or not aid.isdigit():
        log.warning(
            "erc8004_artifact_validation_emit skipped: missing rpc, private key, registry, validator, or onchain agent id"
        )
        return {"ok": False, "skipped": True, "reason": "incomplete_config"}

    try:
        from eth_abi import encode
        from web3 import Web3
    except ImportError as e:
        log.warning("erc8004_artifact_validation_emit skipped: %s", e)
        return {"ok": False, "skipped": True, "reason": "missing_web3"}

    model = Erc8004ValidationRequestPayload(
        agent_id_config=aid,
        validator_address_placeholder=val,
        inputs={
            "source": "veritrade_artifact_emit",
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "related_id": related_id,
            "artifact_json_path": str(artifact_json_path.resolve()),
            "payload": payload,
        },
        outputs={},
    )
    payload_dict = model.model_dump()
    request_hash_hex = validation_request_hash_from_canonical_payload(payload_dict)
    request_hash = Web3.to_bytes(hexstr=request_hash_hex)

    api_base = settings.veritrade_api_base_url.rstrip("/")
    request_uri = f"{api_base}/challenge/erc8004-shapes#artifact_{artifact_id}"

    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        log.warning("erc8004_artifact_validation_emit: rpc not connected")
        return {"ok": False, "error": "rpc_not_connected"}

    acct = w3.eth.account.from_key(pk)
    reg_c = Web3.to_checksum_address(reg)
    val_c = Web3.to_checksum_address(val)
    agent_id = int(aid)

    sel = _selector("validationRequest(address,uint256,string,bytes32)")
    body = encode(["address", "uint256", "string", "bytes32"], [val_c, agent_id, request_uri, request_hash])
    tx: dict[str, Any] = {
        "from": acct.address,
        "to": reg_c,
        "data": sel + body,
        "gas": 500_000,
        "chainId": w3.eth.chain_id,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gasPrice": w3.eth.gas_price,
    }
    try:
        signed = acct.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        rc = w3.eth.wait_for_transaction_receipt(h)
    except Exception as e:
        log.warning("erc8004_artifact_validation_emit failed: %s", e)
        return {"ok": False, "error": str(e)}

    out = {
        "ok": bool(rc.status),
        "tx_hash": h.hex(),
        "request_hash": request_hash_hex,
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
    }
    log.info("erc8004_artifact_validation_emit %s", json.dumps(out, default=str))
    return out
