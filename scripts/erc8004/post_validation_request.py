#!/usr/bin/env python3
"""
Post an EIP-8004-shaped validationRequest on-chain (local/testnet) using Web3.

Computes requestHash the same way as the API helper: keccak256 of canonical JSON payload.

Example:
  python scripts/erc8004/post_validation_request.py \\
    --rpc http://127.0.0.1:8545 \\
    --private-key 0xac0974... \\
    --registry 0xYourValidationRegistry \\
    --validator 0x0000000000000000000000000000000000000B01 \\
    --agent-id 1 \\
    --request-uri https://example/req.json \\
    --payload-json-file path/to/payload.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[2] / "apps" / "api"
sys.path.insert(0, str(_API_DIR))
os.chdir(_API_DIR)

from eth_abi import encode
from eth_utils import keccak

from app.challenge.erc8004_validation import validation_request_hash_from_canonical_payload


def _selector(sig: str) -> bytes:
    return keccak(text=sig)[:4]


def main() -> None:
    try:
        from web3 import Web3
    except ImportError as e:
        raise SystemExit("web3 is required: pip install web3") from e

    p = argparse.ArgumentParser()
    p.add_argument("--rpc", required=True)
    p.add_argument("--private-key", required=True)
    p.add_argument("--registry", required=True, help="VeriTradeLocalValidationRegistry address")
    p.add_argument("--validator", required=True)
    p.add_argument("--agent-id", type=int, required=True)
    p.add_argument("--request-uri", required=True)
    p.add_argument("--payload-json-file", type=Path, required=True)
    args = p.parse_args()

    payload = json.loads(args.payload_json_file.read_text(encoding="utf-8"))
    request_hash_hex = validation_request_hash_from_canonical_payload(payload)
    request_hash = Web3.to_bytes(hexstr=request_hash_hex)

    w3 = Web3(Web3.HTTPProvider(args.rpc))
    acct = w3.eth.account.from_key(args.private_key.strip())
    reg = Web3.to_checksum_address(args.registry.strip())
    val = Web3.to_checksum_address(args.validator.strip())

    sel = _selector("validationRequest(address,uint256,string,bytes32)")
    body = encode(
        ["address", "uint256", "string", "bytes32"],
        [val, args.agent_id, args.request_uri, request_hash],
    )
    tx = {
        "from": acct.address,
        "to": reg,
        "data": sel + body,
        "gas": 500_000,
        "chainId": w3.eth.chain_id,
        "nonce": w3.eth.get_transaction_count(acct.address),
    }
    tx["gasPrice"] = w3.eth.gas_price
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rc = w3.eth.wait_for_transaction_receipt(h)
    print(json.dumps({"tx_hash": h.hex(), "status": rc.status, "request_hash": request_hash_hex}, indent=2))


if __name__ == "__main__":
    main()
