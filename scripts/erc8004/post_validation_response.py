#!/usr/bin/env python3
"""
Post validationResponse on VeriTradeLocalValidationRegistry (local/testnet).

The caller must be the validatorAddress used in the matching validationRequest.
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


def _selector(sig: str) -> bytes:
    return keccak(text=sig)[:4]


def main() -> None:
    try:
        from web3 import Web3
    except ImportError as e:
        raise SystemExit("web3 is required: pip install web3") from e

    p = argparse.ArgumentParser()
    p.add_argument("--rpc", required=True)
    p.add_argument("--private-key", required=True, help="Must be the validator key from validationRequest")
    p.add_argument("--registry", required=True, help="VeriTradeLocalValidationRegistry address")
    p.add_argument("--request-hash", required=True, help="0x-prefixed bytes32 from the request")
    p.add_argument("--response", type=int, required=True, help="uint8 response code")
    p.add_argument("--response-uri", default="", help="responseURI string")
    p.add_argument(
        "--response-hash",
        default="0x0000000000000000000000000000000000000000000000000000000000000000",
        help="bytes32 responseHash (0x…); use keccak of body when committing",
    )
    p.add_argument("--tag", default="", help="tag string")
    args = p.parse_args()

    w3 = Web3(Web3.HTTPProvider(args.rpc))
    acct = w3.eth.account.from_key(args.private_key.strip())
    reg = Web3.to_checksum_address(args.registry.strip())
    req = Web3.to_bytes(hexstr=args.request_hash.strip())
    rh = Web3.to_bytes(hexstr=args.response_hash.strip())

    sel = _selector("validationResponse(bytes32,uint8,string,bytes32,string)")
    body = encode(
        ["bytes32", "uint8", "string", "bytes32", "string"],
        [req, args.response, args.response_uri, rh, args.tag],
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
    print(json.dumps({"tx_hash": h.hex(), "status": rc.status, "from": acct.address}, indent=2))


if __name__ == "__main__":
    main()
