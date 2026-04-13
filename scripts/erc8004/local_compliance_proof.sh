#!/usr/bin/env bash
set -euo pipefail
cat <<'EOF'
=== VeriTrade ERC-8004 local compliance proof (commands only) ===

Terminal A — Anvil:
  anvil --port 8545

Terminal B — one-shot on-chain walk + evidence JSON:
  cd local-registry
  export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
  forge script script/LocalProofBundle.s.sol:LocalProofBundle \
    --rpc-url http://127.0.0.1:8545 --broadcast --sig "run()" -vvvv

Artifact:
  local-registry/evidence/latest-local-proof.json

Unit evidence (no chain):
  cd local-registry
  forge test -vvv --match-test testComplianceEvidence_identityValidationReputationChain

API read surface (after binding .env from script logs):
  GET /challenge/erc8004/onchain-read?validation_request_hash=<from JSON>

docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md
docs/erc8004-compliance-matrix.md
EOF
