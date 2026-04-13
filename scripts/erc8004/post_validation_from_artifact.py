#!/usr/bin/env python3
"""
Optional bridge: build a validationRequest tx from a JSON payload file (same hash as post_validation_request.py).

Does not read the live DB — pass a JSON file exported from artifacts or hand-built.
Safe default: --dry-run prints request_hash and calldata summary without sending.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[2] / "apps" / "api"
sys.path.insert(0, str(_API_DIR))

from app.challenge.erc8004_validation import validation_request_hash_from_canonical_payload


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--payload-json-file", type=Path, required=True)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print request_hash (no web3 / no tx)",
    )
    p.add_argument("--rpc", default="http://127.0.0.1:8545")
    p.add_argument("--private-key", default="", help="Deployer or any funded Anvil key")
    p.add_argument("--registry", default="", help="VeriTradeLocalValidationRegistry")
    p.add_argument("--validator", default="", help="Validator address for validationRequest")
    p.add_argument("--agent-id", type=int, default=1)
    p.add_argument("--request-uri", default="http://127.0.0.1:34120/challenge/erc8004-shapes")
    args = p.parse_args()

    payload = json.loads(args.payload_json_file.read_text(encoding="utf-8"))
    h = validation_request_hash_from_canonical_payload(payload)
    print(json.dumps({"request_hash": h, "dry_run": args.dry_run}, indent=2))

    if args.dry_run:
        return

    if not args.private_key or not args.registry or not args.validator:
        raise SystemExit("For broadcast: pass --private-key --registry --validator (or use --dry-run).")

    import subprocess

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "post_validation_request.py"),
        "--rpc",
        args.rpc,
        "--private-key",
        args.private_key,
        "--registry",
        args.registry,
        "--validator",
        args.validator,
        "--agent-id",
        str(args.agent_id),
        "--request-uri",
        args.request_uri,
        "--payload-json-file",
        str(args.payload_json_file.resolve()),
    ]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
