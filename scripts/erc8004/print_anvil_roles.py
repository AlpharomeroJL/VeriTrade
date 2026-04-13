#!/usr/bin/env python3
"""Print default Anvil account role mapping for VeriTrade ERC-8004 local work (public test keys only)."""

from __future__ import annotations

import json
import sys

try:
    from eth_account import Account
except ImportError as e:
    print("Install eth-account: pip install eth-account", file=sys.stderr)
    raise SystemExit(1) from e

# Default Anvil / Hardhat test mnemonic first three keys (same as `anvil` defaults)
# Must match `anvil` stdout for the same Foundry version (1.6+ uses updated account #1 key).
_KEYS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
]
_ROLES = ["deployer", "agent_owner", "validator_reputation_client"]


def main() -> None:
    rows = []
    for i, (role, pk) in enumerate(zip(_ROLES, _KEYS, strict=True)):
        acct = Account.from_key(pk)
        rows.append(
            {
                "anvil_index": i,
                "role": role,
                "address": acct.address,
                "env_hint": "PRIVATE_KEY" if i == 0 else ("AGENT_PRIVATE_KEY" if i == 1 else "VALIDATOR_PRIVATE_KEY"),
            }
        )
    print(json.dumps({"chain_id_hint": 31337, "accounts": rows}, indent=2))
    print("\n# Export for forge (example - deployer only):", file=sys.stderr)
    print(f"# export PRIVATE_KEY={_KEYS[0]}", file=sys.stderr)


if __name__ == "__main__":
    main()
