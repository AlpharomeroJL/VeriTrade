"""EIP-712 typed-data helper for `VeriTradeLocalIdentityRegistry` SetAgentWallet (local demos)."""

from __future__ import annotations

from typing import Any


def build_set_agent_wallet_typed_data(
    *,
    chain_id: int,
    verifying_contract: str,
    agent_id: int,
    new_wallet: str,
    nonce: int,
) -> dict[str, Any]:
    """
    Matches `VeriTradeLocalIdentityRegistry` (OZ EIP712 domain name/version + chain-bound verifying contract).

    Primary type: `SetAgentWallet(uint256 agentId,address newWallet,uint256 nonce)`
    """
    vc = verifying_contract.strip()
    if not vc.startswith("0x"):
        raise ValueError("verifying_contract must be 0x-prefixed")

    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "SetAgentWallet": [
                {"name": "agentId", "type": "uint256"},
                {"name": "newWallet", "type": "address"},
                {"name": "nonce", "type": "uint256"},
            ],
        },
        "primaryType": "SetAgentWallet",
        "domain": {
            "name": "VeriTradeLocalIdentityRegistry",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": vc,
        },
        "message": {
            "agentId": agent_id,
            "newWallet": new_wallet,
            "nonce": nonce,
        },
    }
