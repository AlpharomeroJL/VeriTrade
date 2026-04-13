"""ERC-1271 verification for VeriTradeEip1271IntentAdapter (optional RPC)."""

from __future__ import annotations

_ERC1271_MAGIC = bytes.fromhex("1626ba7e")


def eip1271_intent_adapter_magic_hex() -> str:
    return "0x1626ba7e"


def verify_eip1271_is_valid_signature(
    rpc_url: str,
    contract_address: str,
    digest_hex: str,
    signature_hex: str,
) -> dict:
    """
    Generic `isValidSignature(bytes32,bytes)` eth_call (ERC-1271 surface).

    Same wire encoding as the VeriTrade intent adapter; works for any contract implementing ERC-1271.
    """
    return verify_trade_intent_eip1271_adapter(rpc_url, contract_address, digest_hex, signature_hex)


def verify_trade_intent_eip1271_adapter(
    rpc_url: str,
    adapter_address: str,
    digest_hex: str,
    signature_hex: str,
) -> dict:
    """
    eth_call `isValidSignature(bytes32,bytes)` on the adapter contract.

    Returns a dict with `ok` (bool), `returned_selector` (hex), `error` (optional).
    """
    try:
        from web3 import Web3
        from eth_abi import encode
        from eth_utils import keccak
    except ImportError as e:
        return {"ok": False, "error": f"missing_dependency:{e!s}"}

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        return {"ok": False, "error": "rpc_not_connected"}

    adapter = Web3.to_checksum_address(adapter_address.strip())
    digest = Web3.to_bytes(hexstr=digest_hex)
    sig = signature_hex.strip()
    if sig.startswith("0x"):
        sig = sig[2:]
    sig_b = bytes.fromhex(sig)

    sel = keccak(text="isValidSignature(bytes32,bytes)")[:4]
    calldata = sel + encode(["bytes32", "bytes"], [digest, sig_b])

    try:
        raw = w3.eth.call({"to": adapter, "data": calldata})
    except Exception as e:
        return {"ok": False, "error": f"eth_call_failed:{e!s}"}

    if len(raw) < 4:
        return {"ok": False, "error": "short_return", "raw": raw.hex()}
    ret = raw[:4]
    ok = ret == _ERC1271_MAGIC
    return {
        "ok": ok,
        "returned_selector": "0x" + ret.hex(),
        "expected_magic": eip1271_intent_adapter_magic_hex(),
    }
