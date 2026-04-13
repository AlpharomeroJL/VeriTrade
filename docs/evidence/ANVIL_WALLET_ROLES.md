# Anvil wallet roles — VeriTrade ERC-8004 local testing

**Scope:** local / dev only. These private keys are **public defaults** shipped with Anvil and Hardhat — **never** use them on mainnet or with real funds.

## Start Anvil

```bash
anvil --port 8545
```

If the port is in use (common on Windows), pick another port and use it consistently everywhere (`--rpc-url`, MetaMask custom RPC, `ERC8004_RPC_URL`).

**Chain ID:** `31337` (default Anvil).

**RPC URL:** `http://127.0.0.1:8545` (or your chosen port).

## Default pre-funded accounts (first three)

| Index | Role in VeriTrade demos | Address |
|-------|-------------------------|---------|
| **0** | **Deployer** — deploys contracts, may pay gas for `validationRequest` in `LocalProofBundle` | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` |
| **1** | **Agent owner** — calls `register`, `setAgentURI`, `setMetadata`; **owner** of `VeriTradeEip1271IntentAdapter` in `LocalProofBundle` | `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` |
| **2** | **Validator + reputation client** — `validationResponse`, `giveFeedback` | `0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC` |

## Private keys (same order — **public test keys**)

Store **only** in local `.env` (never commit). Defaults are documented so you can copy from [`.env.anvil.example`](../../.env.anvil.example).

| Variable | Typical value (Anvil #0 / #1 / #2) |
|----------|-------------------------------------|
| `PRIVATE_KEY` | Account **0** deployer key (see `.env.anvil.example`) |
| `AGENT_PRIVATE_KEY` | Optional; defaults to account **1** in `LocalProofBundle` if unset |
| `VALIDATOR_PRIVATE_KEY` | Optional; defaults to account **2** in `LocalProofBundle` if unset |

Exact hex strings: run `python scripts/erc8004/print_anvil_roles.py` from repo root (keys are taken from **Foundry 1.6+ `anvil` stdout**; older blog posts may show a different account-#1 key).

## EIP-712 + ERC-1271 alignment (`LocalProofBundle`)

- `VeriTradeEip1271IntentAdapter` **owner** = **agent (account 1)**.
- Set `VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT` = adapter address from evidence JSON.
- Set `VERITRADE_INTENT_SIGNER_PRIVATE_KEY` = **`AGENT_PRIVATE_KEY`** (same as account 1 default) so typed intents verify against the adapter.

## MetaMask / Rabby (optional manual import)

1. Add **network**: RPC `http://127.0.0.1:8545`, chain id **31337**, currency symbol **ETH** (any name, e.g. “Anvil Local”).
2. **Import private key** (Account → Import) using **only** a throwaway Anvil key from this doc or `print_anvil_roles.py`.
3. Inspect txs/logs on the local chain — **no** bridge to mainnet.

## Repo helpers

| Helper | Purpose |
|--------|---------|
| `python scripts/erc8004/print_anvil_roles.py` | Print addresses + env variable names (no secrets beyond public Anvil keys). |
| `pwsh scripts/erc8004/prove_local_slice.ps1` / `bash scripts/erc8004/prove_local_slice.sh` | Shortest scripted check: roles + forge unit test + reminder to run `LocalProofBundle` against a running Anvil. |
| `local-registry/script/LocalProofBundle.s.sol` | Full deploy + mint + metadata + validation + reputation + `evidence/latest-local-proof.json`. |

## Triage reference

See [MATRIX_TRIAGE.md](MATRIX_TRIAGE.md).
