#!/usr/bin/env python3
"""
Post giveFeedback on VeriTradeLocalReputationRegistry (local/testnet).

msg.sender becomes clientAddress in NewFeedback (use a distinct feedback key if needed).
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
    p.add_argument("--private-key", required=True)
    p.add_argument("--registry", required=True, help="VeriTradeLocalReputationRegistry address")
    p.add_argument("--agent-id", type=int, required=True)
    p.add_argument("--value", type=int, default=10, help="int128 feedback value")
    p.add_argument("--value-decimals", type=int, default=0)
    p.add_argument("--tag1", default="integration")
    p.add_argument("--tag2", default="latency")
    p.add_argument("--endpoint", default="http://127.0.0.1:34120")
    p.add_argument("--feedback-uri", default="ipfs://veritrade/feedback.json")
    p.add_argument(
        "--feedback-hash",
        default="0x" + "00" * 32,
        help="bytes32 feedbackHash commitment",
    )
    args = p.parse_args()

    w3 = Web3(Web3.HTTPProvider(args.rpc))
    acct = w3.eth.account.from_key(args.private_key.strip())
    reg = Web3.to_checksum_address(args.registry.strip())
    fh = Web3.to_bytes(hexstr=args.feedback_hash.strip())

    sel = _selector(
        "giveFeedback(uint256,int128,uint8,string,string,string,string,bytes32)"
    )
    body = encode(
        ["uint256", "int128", "uint8", "string", "string", "string", "string", "bytes32"],
        [
            args.agent_id,
            args.value,
            args.value_decimals,
            args.tag1,
            args.tag2,
            args.endpoint,
            args.feedback_uri,
            fh,
        ],
    )
    tx = {
        "from": acct.address,
        "to": reg,
        "data": sel + body,
        "gas": 800_000,
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
