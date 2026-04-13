#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "== 1) Anvil wallet roles (public defaults) =="
python scripts/erc8004/print_anvil_roles.py

echo ""
echo "== 2) Foundry unit proof (no chain) =="
cd local-registry
forge test -vvv --match-test testComplianceEvidence_identityValidationReputationChain

echo ""
echo "== 3) Full on-chain bundle (requires Anvil in another terminal) =="
echo "  anvil --port 8545"
echo "  cd local-registry"
echo "  export PRIVATE_KEY=<deployer key from print_anvil_roles>"
echo "  forge script script/LocalProofBundle.s.sol:LocalProofBundle --rpc-url http://127.0.0.1:8545 --broadcast --sig \"run()\" -vvvv"
echo ""
echo "See docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md and docs/evidence/ANVIL_WALLET_ROLES.md"
