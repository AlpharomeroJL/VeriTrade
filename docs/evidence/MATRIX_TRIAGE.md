# Matrix triage (this pass) — ERC-8004

Source: [../erc8004-compliance-matrix.md](../erc8004-compliance-matrix.md).

**Note:** Anvil default **private keys** must match your Foundry `anvil` version (1.6+ changed account #1’s key vs older blog posts). Use `anvil` stdout or `print_anvil_roles.py`.

## Attack now (high leverage, local-only)

| Row | Rationale |
|-----|-----------|
| **I5** metadata KV | Truthful subset: `setMetadata` / `getMetadata` on local Identity — closes “not implemented” without claiming full draft wallet proofs. |
| **P3** reputation reads | Add **`feedbackCount(client, agentId)`** view + API/script reads — materially improves “read/query” without an indexer. |
| **X / reproducibility** | Multi-role **Anvil wallet workflow** (deployer / agent / validator), deterministic env template, `print_anvil_roles` + **`prove_local_slice`** scripts. |
| **LocalProofBundle** | Use **three Anvil roles** (mint as agent, validate as validator, adapter owner = agent for EIP-712 realism). |
| **R3 / registration** | Optional **`agentWallet`** field in served JSON when `VERITRADE_AGENT_WALLET_PLACEHOLDER` set — stronger binding narrative (still not on-chain proof). |
| **K1** ERC-1271 | Forge test: **wrong signer → non-magic** (`0xffffffff`) — defensible realism without faking Safe. |

## Strengthen (partial → clearer proof)

| Row | Action |
|-----|--------|
| **V4** | Extend `GET /challenge/erc8004/onchain-read` with optional **reputation** + **identity metadata** query params. |
| **R2** | Walkthrough links **`prove_local_slice`** + export script reminder. |

## Remain deferred (honest)

| Row | Why |
|-----|-----|
| **I6** full `agentWallet` EIP-712 update flow | Normative protocol + wallet UX beyond local demo scope. |
| **E2** PKI / DNSSEC | Ops / hosting, out of scope. |
| **V5** automatic trading-loop → chain | Still optional **script-only** bridge (`post_validation_from_artifact.py`); no default pipeline coupling. |
| **T4 / K3** generic smart wallets | Not implemented; adapter path only. |
| **Mainnet canonical registries** | Blocker list unchanged. |
