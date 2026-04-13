#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/local-registry"

command -v forge >/dev/null 2>&1 || { echo "install Foundry: https://book.getfoundry.sh/getting-started/installation"; exit 1; }

test -d lib/forge-std || forge install foundry-rs/forge-std@v1.9.4 --no-git
test -d lib/openzeppelin-contracts || forge install OpenZeppelin/openzeppelin-contracts@v5.0.2 --no-git

forge build
forge test -vvv
echo "OK"
