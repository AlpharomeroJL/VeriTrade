# What maps to ERC-8004 (draft-aligned; local dev extensions)

[ERC-8004 / EIP-8004](https://eips.ethereum.org/EIPS/eip-8004) describes **Identity**, **Reputation**, and **Validation** registries plus a **registration JSON** reachable from **`agentURI`**. VeriTrade maps **honestly** to those ideas with **off-chain artifacts and API surfaces**, and adds **optional local-chain** building blocks that are **not** automatic production integration.

**Authoritative alignment write-up:** [erc8004-alignment.md](erc8004-alignment.md)

## Mappings

| ERC-8004 theme | VeriTrade slice |
|----------------|-----------------|
| **Identity Registry** | Stable `VERITRADE_AGENT_ID`; optional `ERC8004_AGENT_URI_STUB`; optional `VERITRADE_AGENT_WALLET_PLACEHOLDER`. **`registrations[]`** is filled from **`ERC8004_IDENTITY_REGISTRY_ADDRESS` + `ERC8004_ONCHAIN_AGENT_ID`** when set (after **your** local `register` mint — see `local-registry/`). |
| **Registration file** | EIP-shaped JSON: `spec-alignment/agent-registration.json`, static **`/.well-known/agent-registration.json`**, and **`GET /challenge/agent-registration`**. **`GET /challenge/agent-registration/verify`** reports fetch / same-host / env-binding checks without claiming CA-grade HTTPS proof. |
| **Validation Registry** | **Runtime:** example JSON + **`keccak256`** helpers + **`GET /challenge/erc8004-shapes`** — **not** auto-sent on-chain. **Local:** `VeriTradeLocalValidationRegistry` emits **`ValidationRequest` / `ValidationResponse`** when **you** call it on Anvil (`local-registry/README.md`). |
| **Reputation Registry** | **Runtime:** off-chain example schema. **Local:** `VeriTradeLocalReputationRegistry` emits **`NewFeedback`**; on-chain **`feedbackCount`** + **`GET /challenge/erc8004/onchain-read`** (optional). |
| **On-chain reads** | **`GET /challenge/erc8004/onchain-read`** — `getValidationStatus`, identity + **`getMetadata`**, reputation **`feedbackCount`** when RPC + env set. |
| **Transparency** | Validation artifact trace, `GET /challenge/context`, intent commitment hash, optional EIP-712 fields on intents. |
| **EIP-712 / wallets** | Optional **typed + signed** trade intents (`app/challenge/eip712_intent.py`) when dev env vars are set; SHA-256 commitment retained. **ERC-1271:** optional `eth_call` to `VeriTradeEip1271IntentAdapter` only (not generic smart wallets). |

## Solidity

| Location | Role |
|----------|------|
| `spec-alignment/contracts/` | Interface stubs — **not deployed**. |
| `local-registry/src/` | **Optional** minimal contracts for Anvil demos; **not** audited. |

## Non-claims

- **Not** “ERC-8004 compliant” or “fully on-chain” in the default configuration.
- **Not** automatic posting to public Identity / Validation / Reputation registries.
- **Intent commitment** today is still **SHA-256 over canonical JSON**; EIP-712 is an **additional** dev-local layer when configured.

## Env (summary)

| Variable | Purpose |
|----------|---------|
| `VERITRADE_AGENT_ID` | Stable agent id string for demos and APIs. |
| `ERC8004_AGENT_URI_STUB` | Optional string for a future on-chain `agentURI` (IPFS/https/etc.). |
| `VERITRADE_AGENT_WALLET_PLACEHOLDER` | Optional `0x…` placeholder string for documentation only — **not verified on-chain**. |
| `ERC8004_IDENTITY_REGISTRY_ADDRESS` / `ERC8004_ONCHAIN_AGENT_ID` | After **local** mint, binds `registrations[]` in the served registration JSON. |
| `ERC8004_DEV_CHAIN_ID` | Chain id for EIP-712 domain (default `31337`). |
| `VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT` / `VERITRADE_INTENT_SIGNER_PRIVATE_KEY` | Optional EIP-712 signing for new trade intents (dev keys only). |

See `.env.example` for the full list.
