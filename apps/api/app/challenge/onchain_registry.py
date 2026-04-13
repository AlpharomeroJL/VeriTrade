"""Optional JSON-RPC reads against VeriTrade local-registry contracts (evidence / debugging)."""

from __future__ import annotations

from typing import Any

_VALIDATION_STATUS_ABI = [
    {
        "name": "getValidationStatus",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "requestHash", "type": "bytes32"}],
        "outputs": [
            {"name": "validatorAddress", "type": "address"},
            {"name": "agentId", "type": "uint256"},
            {"name": "response", "type": "uint8"},
            {"name": "responseHash", "type": "bytes32"},
            {"name": "tag", "type": "string"},
            {"name": "lastUpdate", "type": "uint256"},
        ],
    }
]

_REPUTATION_FEEDBACK_COUNT_ABI = [
    {
        "name": "feedbackCount",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "client", "type": "address"},
            {"name": "agentId", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "uint64"}],
    }
]

_IDENTITY_METADATA_ABI = [
    {
        "name": "getMetadata",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "key", "type": "string"},
        ],
        "outputs": [{"name": "", "type": "string"}],
    }
]

_IDENTITY_AGENT_URI_ABI = [
    {
        "name": "agentURI",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "string"}],
    },
    {
        "name": "ownerOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "name": "exists",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "agentWallet",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "name": "walletNonce",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]

_REPUTATION_GET_FEEDBACK_ABI = [
    {
        "name": "getFeedback",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "client", "type": "address"},
            {"name": "agentId", "type": "uint256"},
            {"name": "index", "type": "uint64"},
        ],
        "outputs": [
            {"name": "value", "type": "int128"},
            {"name": "valueDecimals", "type": "uint8"},
            {"name": "tag1", "type": "string"},
            {"name": "tag2", "type": "string"},
            {"name": "endpoint", "type": "string"},
            {"name": "feedbackURI", "type": "string"},
            {"name": "feedbackHash", "type": "bytes32"},
        ],
    }
]


def read_local_validation_status(
    rpc_url: str,
    validation_registry_address: str,
    request_hash_hex: str,
) -> dict[str, Any]:
    """
    eth_call getValidationStatus(bytes32) on VeriTradeLocalValidationRegistry.

    request_hash_hex: 0x-prefixed 32-byte hash.
    """
    try:
        from web3 import Web3
    except ImportError as e:
        return {"ok": False, "error": f"missing_dependency:{e!s}"}

    w3 = Web3(Web3.HTTPProvider(rpc_url.strip()))
    if not w3.is_connected():
        return {"ok": False, "error": "rpc_not_connected"}

    reg = Web3.to_checksum_address(validation_registry_address.strip())
    h = request_hash_hex.strip()
    if not h.startswith("0x") or len(h) != 66:
        return {"ok": False, "error": "invalid_request_hash_hex"}

    contract = w3.eth.contract(address=reg, abi=_VALIDATION_STATUS_ABI)
    try:
        out = contract.functions.getValidationStatus(Web3.to_bytes(hexstr=h)).call()
    except Exception as e:
        return {"ok": False, "error": f"eth_call_failed:{e!s}"}

    validator_address, agent_id, response, response_hash, tag, last_update = out
    if isinstance(response_hash, (bytes, bytearray)):
        rh_hex = "0x" + bytes(response_hash).hex()
    else:
        rh_hex = str(response_hash)
    return {
        "ok": True,
        "chain_id": w3.eth.chain_id,
        "validator_address": validator_address,
        "agent_id": int(agent_id),
        "response": int(response),
        "response_hash": rh_hex,
        "tag": tag,
        "last_update": int(last_update),
    }


def read_local_identity_agent(
    rpc_url: str,
    identity_registry_address: str,
    agent_id: int,
) -> dict[str, Any]:
    """eth_call agentURI, ownerOf, exists for evidence."""
    try:
        from web3 import Web3
    except ImportError as e:
        return {"ok": False, "error": f"missing_dependency:{e!s}"}

    w3 = Web3(Web3.HTTPProvider(rpc_url.strip()))
    if not w3.is_connected():
        return {"ok": False, "error": "rpc_not_connected"}

    ident = Web3.to_checksum_address(identity_registry_address.strip())
    contract = w3.eth.contract(address=ident, abi=_IDENTITY_AGENT_URI_ABI)
    try:
        uri = contract.functions.agentURI(agent_id).call()
        owner = contract.functions.ownerOf(agent_id).call()
        ex = contract.functions.exists(agent_id).call()
        agent_wallet = None
        wallet_nonce = None
        try:
            agent_wallet = contract.functions.agentWallet(agent_id).call()
            wallet_nonce = int(contract.functions.walletNonce(agent_id).call())
        except Exception:
            pass
    except Exception as e:
        return {"ok": False, "error": f"eth_call_failed:{e!s}"}

    out: dict[str, Any] = {
        "ok": True,
        "chain_id": w3.eth.chain_id,
        "agent_id": agent_id,
        "agent_uri": uri,
        "owner": owner,
        "exists": bool(ex),
    }
    if agent_wallet is not None:
        out["agent_wallet"] = agent_wallet
    if wallet_nonce is not None:
        out["wallet_nonce"] = wallet_nonce
    return out


def read_reputation_feedback_count(
    rpc_url: str,
    reputation_registry_address: str,
    client_address: str,
    agent_id: int,
) -> dict[str, Any]:
    try:
        from web3 import Web3
    except ImportError as e:
        return {"ok": False, "error": f"missing_dependency:{e!s}"}

    w3 = Web3(Web3.HTTPProvider(rpc_url.strip()))
    if not w3.is_connected():
        return {"ok": False, "error": "rpc_not_connected"}

    reg = Web3.to_checksum_address(reputation_registry_address.strip())
    client = Web3.to_checksum_address(client_address.strip())
    contract = w3.eth.contract(address=reg, abi=_REPUTATION_FEEDBACK_COUNT_ABI)
    try:
        n = contract.functions.feedbackCount(client, agent_id).call()
    except Exception as e:
        return {"ok": False, "error": f"eth_call_failed:{e!s}"}

    return {"ok": True, "chain_id": w3.eth.chain_id, "client": client, "agent_id": agent_id, "feedback_count": int(n)}


def read_reputation_feedback_at_index(
    rpc_url: str,
    reputation_registry_address: str,
    client_address: str,
    agent_id: int,
    feedback_index: int,
) -> dict[str, Any]:
    try:
        from web3 import Web3
    except ImportError as e:
        return {"ok": False, "error": f"missing_dependency:{e!s}"}

    w3 = Web3(Web3.HTTPProvider(rpc_url.strip()))
    if not w3.is_connected():
        return {"ok": False, "error": "rpc_not_connected"}

    reg = Web3.to_checksum_address(reputation_registry_address.strip())
    client = Web3.to_checksum_address(client_address.strip())
    contract = w3.eth.contract(address=reg, abi=_REPUTATION_GET_FEEDBACK_ABI)
    try:
        tup = contract.functions.getFeedback(client, agent_id, feedback_index).call()
    except Exception as e:
        return {"ok": False, "error": f"eth_call_failed:{e!s}"}

    value, dec, tag1, tag2, endpoint, fb_uri, fb_hash = tup
    fh = fb_hash if isinstance(fb_hash, str) else ("0x" + bytes(fb_hash).hex() if fb_hash is not None else None)
    return {
        "ok": True,
        "chain_id": w3.eth.chain_id,
        "client": client,
        "agent_id": agent_id,
        "feedback_index": feedback_index,
        "value": int(value),
        "value_decimals": int(dec),
        "tag1": tag1,
        "tag2": tag2,
        "endpoint": endpoint,
        "feedback_uri": fb_uri,
        "feedback_hash": fh,
    }


def read_identity_metadata_value(
    rpc_url: str,
    identity_registry_address: str,
    agent_id: int,
    metadata_key: str,
) -> dict[str, Any]:
    try:
        from web3 import Web3
    except ImportError as e:
        return {"ok": False, "error": f"missing_dependency:{e!s}"}

    w3 = Web3(Web3.HTTPProvider(rpc_url.strip()))
    if not w3.is_connected():
        return {"ok": False, "error": "rpc_not_connected"}

    ident = Web3.to_checksum_address(identity_registry_address.strip())
    contract = w3.eth.contract(address=ident, abi=_IDENTITY_METADATA_ABI)
    try:
        val = contract.functions.getMetadata(agent_id, metadata_key).call()
    except Exception as e:
        return {"ok": False, "error": f"eth_call_failed:{e!s}"}

    return {
        "ok": True,
        "chain_id": w3.eth.chain_id,
        "agent_id": agent_id,
        "metadata_key": metadata_key,
        "metadata_value": val,
    }


def build_onchain_read_report(
    rpc_url: str | None,
    validation_registry_address: str | None,
    identity_registry_address: str | None,
    reputation_registry_address: str | None,
    onchain_agent_id: str | None,
    validation_request_hash: str | None,
    reputation_client_address: str | None = None,
    reputation_feedback_agent_id: int | None = None,
    identity_metadata_key: str | None = None,
    reputation_feedback_index: int | None = None,
) -> dict[str, Any]:
    """
    Aggregate truthful read surface for judges (no chain writes).

    When RPC or addresses are missing, returns explicit `skipped_reason` entries.
    """
    report: dict[str, Any] = {
        "rpc_configured": bool(rpc_url and rpc_url.strip()),
        "validation_registry_configured": bool(validation_registry_address and validation_registry_address.strip()),
        "identity_registry_configured": bool(identity_registry_address and identity_registry_address.strip()),
        "reputation_registry_configured": bool(reputation_registry_address and reputation_registry_address.strip()),
        "onchain_agent_id_configured": bool(onchain_agent_id and str(onchain_agent_id).strip()),
        "validation": None,
        "identity": None,
        "reputation_feedback_count": None,
        "reputation_feedback_at_index": None,
        "identity_metadata": None,
        "notes": [
            "Read-only eth_call against optional local-registry deployments (Anvil / testnet).",
            "Does not assert mainnet registry compliance or canonical ERC-8004 bytecode.",
        ],
    }

    if not report["rpc_configured"]:
        report["skipped_reason"] = "ERC8004_RPC_URL unset"
        return report

    rpc = (rpc_url or "").strip()
    vreg = (validation_registry_address or "").strip()
    ireg = (identity_registry_address or "").strip()
    rreg = (reputation_registry_address or "").strip()
    vhash = (validation_request_hash or "").strip()
    rclient = (reputation_client_address or "").strip()
    imeta_key = (identity_metadata_key or "").strip()

    if vhash and report["validation_registry_configured"]:
        report["validation"] = read_local_validation_status(rpc, vreg, vhash)
    elif vhash:
        report["validation"] = {"ok": False, "error": "validation_registry_address unset"}

    if report["identity_registry_configured"] and onchain_agent_id and str(onchain_agent_id).strip().isdigit():
        aid = int(str(onchain_agent_id).strip())
        report["identity"] = read_local_identity_agent(rpc, ireg, aid)
        if imeta_key:
            report["identity_metadata"] = read_identity_metadata_value(rpc, ireg, aid, imeta_key)

    if (
        report["reputation_registry_configured"]
        and rclient
        and reputation_feedback_agent_id is not None
        and onchain_agent_id
        and str(onchain_agent_id).strip().isdigit()
    ):
        report["reputation_feedback_count"] = read_reputation_feedback_count(
            rpc,
            rreg,
            rclient,
            int(str(onchain_agent_id).strip()),
        )

    if (
        report["reputation_registry_configured"]
        and rclient
        and reputation_feedback_index is not None
        and onchain_agent_id
        and str(onchain_agent_id).strip().isdigit()
    ):
        report["reputation_feedback_at_index"] = read_reputation_feedback_at_index(
            rpc,
            rreg,
            rclient,
            int(str(onchain_agent_id).strip()),
            int(reputation_feedback_index),
        )

    return report
