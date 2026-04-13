#!/usr/bin/env bash
# Deploy VeriTrade local-registry stack to Ethereum Sepolia and mint agent #1.
# Prerequisites: Foundry, funded PRIVATE_KEY on Sepolia, PUBLIC_AGENT_REGISTRATION_URL set.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/local-registry"

if [[ -z "${PRIVATE_KEY:-}" ]]; then
  echo "error: set PRIVATE_KEY (0x-prefixed deployer key with Sepolia ETH)" >&2
  exit 1
fi
if [[ -z "${PUBLIC_AGENT_REGISTRATION_URL:-}" ]]; then
  echo "error: set PUBLIC_AGENT_REGISTRATION_URL to your live HTTPS registration URL" >&2
  exit 1
fi

RPC="${SEPOLIA_RPC_URL:-https://ethereum-sepolia.publicnode.com}"

echo "Using RPC: $RPC"
forge script script/SepoliaDeployAndMint.s.sol:SepoliaDeployAndMint \
  --rpc-url "$RPC" \
  --broadcast \
  --sig "run()" \
  -vvvv

echo ""
echo "Wrote local-registry/evidence/sepolia-public-proof.json (gitignored). Paste NEXT_BIND_ENV lines into API .env and redeploy/sync static registration."
