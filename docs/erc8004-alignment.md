# ERC-8004 draft alignment (VeriTrade)

This document is the **single judge-readable alignment** between [EIP-8004: Trustless Agents (DRAFT)](https://eips.ethereum.org/EIPS/eip-8004) and this repository. VeriTrade is **not** claiming full protocol compliance or live registry deployment.

**Machine-readable conformance matrix (requirement × status × proof):** [erc8004-compliance-matrix.md](erc8004-compliance-matrix.md).  
**Summary checklist:** [erc8004-compliance-checklist.md](erc8004-compliance-checklist.md).

## 1. What ERC-8004 expects (summary)

Three registries:

1. **Identity Registry** — ERC-721-style agent handle; `agentURI` resolves to a **registration JSON** with `type`, `name`, `description`, `image`, `services`, optional `supportedTrust`, optional `registrations[]` binding `agentId` + `agentRegistry`.
2. **Reputation Registry** — `giveFeedback` and related read paths; optional off-chain feedback JSON.
3. **Validation Registry** — `validationRequest(validatorAddress, agentId, requestURI, requestHash)` and `validationResponse(requestHash, response, …)` with `requestHash` / `responseHash` as cryptographic commitments.

The EIP also describes **agentWallet** (reserved metadata), **EIP-712** wallet proofs for wallet changes, and optional **ERC-1271** for contract wallets.

## 2. What VeriTrade implements today

| Area | Implementation |
|------|----------------|
| **Registration file** | Real JSON at `spec-alignment/agent-registration.json`, mirrored under `apps/web/public/.well-known/agent-registration.json`, and **`GET /challenge/agent-registration`** (endpoints merged from `.env`). `type` matches the EIP registration `type` string. **`registrations[]`** is **empty by default**; when `ERC8004_IDENTITY_REGISTRY_ADDRESS` and `ERC8004_ONCHAIN_AGENT_ID` are set (after a **local or Sepolia** mint), the API fills `registrations` with `agentRegistry`, `agentId`, and `agentURI` (effective URI from stub or `/.well-known/...`). |
| **Domain / file checks** | **`GET /challenge/agent-registration/verify`** — best-effort fetches of the static `/.well-known` URL vs the API registration JSON, same-host checks, comparison of `registrations` to env binding, **`registrations_agent_uri`** (fetch the configured on-chain `agentURI` document), and optional **`transport_observation`** on `https://` URLs. **Does not** assert CA-trusted HTTPS policy or production domain control. |
| **On-chain reads (optional)** | **`GET /challenge/erc8004/onchain-read`** — when `ERC8004_RPC_URL` and registry env vars are set, read-only `eth_call` to `getValidationStatus`, identity `agentURI` / `ownerOf` / optional **`agentWallet`** / **`walletNonce`**, optional **`getMetadata`**, optional **`feedbackCount`**, optional **`getFeedback`** by index, optional registration **`agentWallet`** string when env set (no writes). |
| **Identity surface** | Stable `VERITRADE_AGENT_ID`, optional `ERC8004_AGENT_URI_STUB`, optional `VERITRADE_AGENT_WALLET_PLACEHOLDER`, and `challenge.erc8004_draft` on **`GET /overview`** / **`GET /challenge/context`** (includes optional env-pasted registry addresses for **local/test** documentation). |
| **Intent binding** | **`intent_commitment_sha256`** — SHA-256 over canonical JSON (unchanged). **Optional EIP-712:** when `VERITRADE_INTENT_SIGNER_PRIVATE_KEY` and a non-zero `VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT` are set, new trade intents get **`eip712_signature` / `eip712_signer` / `eip712_chain_id`** persisted (`eth-account`, `ERC8004_DEV_CHAIN_ID`). See [intent-envelope.md](intent-envelope.md). `trade_intent_eip712_outline()` remains a **zero-bound** outline for judges when no domain is configured. |
| **Validation-shaped artifacts** | Example payloads: `spec-alignment/schemas/*.json` and **`GET /challenge/erc8004-shapes`**. **`keccak256`** helper in `app.challenge.erc8004_validation`. **Default:** no on-chain emit from the API loop. **Opt-in:** `ERC8004_ARTIFACT_VALIDATION_EMIT_ENABLED` + env may emit `validationRequest` from selected artifact writes (`erc8004_artifact_validation_bridge.py`); optional **`scripts/erc8004/post_validation_request.py`** / **`post_validation_response.py`**. |
| **Reputation-shaped (minimal)** | `spec-alignment/schemas/reputation-feedback.offchain.example.json` — **explicitly local / not on-chain** from the trading pipeline. |
| **Solidity — interfaces** | `spec-alignment/contracts/*.sol` — **illustrative interfaces** (see that folder’s README). |
| **Solidity — local demo contracts** | `local-registry/src/*.sol` — **optional** Identity / Validation / Reputation / EIP-1271 adapter. **Anvil:** `LocalProofBundle.s.sol` + `ANVIL_WALLET_ROLES.md`. **Public Sepolia (operator):** `SepoliaDeployAndMint.s.sol` + `PUBLIC_SEPOLIA_DEPLOY.md` + `deploy_sepolia.*` — **not** a protocol-mandated canonical mainnet registry. |

## 3. What is simulated vs real

| Item | Status |
|------|--------|
| Order execution | **Simulated** paper by default (`ALLOW_REAL_ORDERS=false`). |
| Market data | **Configurable** — demo, Kraken public HTTPS, or Kraken CLI per `.env`. |
| Artifacts in DB / `artifacts/` | **Real** persisted records from runs. |
| **Default** on-chain registries | **Not auto-deployed** or invoked by the trading loop. |
| **`registrations[]`** | **Empty** unless operator sets env after a **local or Sepolia** mint (or copies equivalent JSON). |
| **Validation / Reputation on-chain** | **Default:** not sent from FastAPI. **Optional:** env-gated artifact → `validationRequest` bridge; **`local-registry`** contracts + `cast` / wallet workflows; `LocalProofBundle`. |
| **EIP-712 trade intents** | **Real** sign + recover path in Python when dev env vars are set; **off** by default (no private key). Optional **ERC-1271 `eth_call`** for the configured verifying contract(s) — primary adapter + optional **secondary** address (wrong signer → `0xffffffff` on-chain for the adapter pattern). **Not** a universal smart-wallet attestation layer. |

## 4. What is draft-aligned but not production registry integration

- The **registration JSON** structure and **`.well-known`** copy.
- **Validation request/response** JSON examples and **keccak256** commitment helper for payloads (EIP semantics).
- **Interface stubs** under `spec-alignment/contracts/`.
- **Local-registry** contracts: developer-owned **Anvil** exercise **or** operator-owned **Sepolia** deployment — not a global “official registry” compliance claim.

## 5. Remaining gaps vs “full” ERC-8004 (honest)

1. **No** protocol-mandated **mainnet canonical** ERC-8004 registry — Sepolia addresses are **operator-deployed** VeriTrade bytecode.
2. **No** automatic default pipeline → `validationRequest` / `giveFeedback` on any network (optional env/scripts only).
3. **No** universal smart-wallet **ERC-1271** matrix — bounded verifier configuration only.
4. **No** production **Web PKI / DNSSEC** proof — verify route remains **technical transparency** (including TLS observation + `agentURI` fetch).

## 6. Repo artifacts introduced for this alignment

| Path | Role |
|------|------|
| `spec-alignment/agent-registration.json` | Canonical registration template (localhost defaults). |
| `apps/web/public/.well-known/agent-registration.json` | Static copy for the web dev server (re-sync via `python scripts/export_agent_registration_static.py`). |
| `apps/web/public/veritrade-agent.svg` | `image` field target for local demos. |
| `spec-alignment/contracts/` | Solidity **illustrative** interfaces. |
| `local-registry/` | **Optional** Foundry project: Identity / Validation / Reputation contracts + README / `cast` examples + **Sepolia** script. |
| `spec-alignment/schemas/` | Example validation + off-chain feedback JSON. |
| `docs/intent-envelope.md` | Intent fields vs SHA-256 vs EIP-712. |
| `apps/api/app/challenge/registration.py` | Builds registration dict from template + settings + optional `registrations[]`. |
| `apps/api/app/challenge/registration_verify.py` | Builds `GET /challenge/agent-registration/verify` report. |
| `apps/api/app/challenge/eip712_intent.py` | EIP-712 typed data + sign + recover. |
| `apps/api/app/challenge/onchain_registry.py` | Optional JSON-RPC reads for local-registry contracts. |
| `apps/api/app/challenge/identity_wallet_eip712.py` | EIP-712 typed-data builder for `SetAgentWallet` (local identity contract). |
| `apps/api/app/challenge/erc8004_artifact_validation_bridge.py` | Opt-in `validationRequest` emission after artifact writes. |
| `apps/api/app/challenge/erc8004_validation.py` | Draft-shaped models + keccak256 helper. |
| `local-registry/script/LocalProofBundle.s.sol` | One-shot deploy + mint + metadata + validation + reputation + evidence JSON (multi-role). |
| `local-registry/script/SepoliaDeployAndMint.s.sol` | Public Sepolia deploy + mint + `evidence/sepolia-public-proof.json`. |
| `docs/evidence/PUBLIC_SEPOLIA_DEPLOY.md` | Operator runbook: Vercel HTTPS `/.well-known`, env binding, Foundry broadcast. |
| `docs/deployment/VERCEL_WEB.md` | Vercel **apps/web** settings for static registration hosting. |
| `docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md` | Reproducible command sequence for local proof. |
| `docs/evidence/ANVIL_WALLET_ROLES.md` | Deployer / agent / validator mapping + MetaMask settings. |
| `.env.anvil.example` | Copy-paste local-only env hints (public Anvil keys). |
| `scripts/erc8004/print_anvil_roles.py` / `prove_local_slice.*` | Role table + shortest scripted proof slice. |
| `docs/erc8004-compliance-matrix.md` | Requirement × status × proof spine. |

## Strongest truthful public phrase

**“VeriTrade is ERC-8004 *draft-aligned* with a real registration file (including public **`/.well-known/agent-registration.json`** when hosted on Vercel), optional env-bound `registrations[]` and **`agentWallet`** surfaces, optional **EIP-712** trade-intent signatures in dev (with **ERC-1271 `eth_call`** against one or two configured verifying contracts), optional **Anvil** *or* **operator-run Ethereum Sepolia** registry contracts (same bytecode; metadata, **`getFeedback`**, validation, multi-role local proof), an **opt-in** artifact→`validationRequest` bridge, reproducible proof paths ([compliance matrix](erc8004-compliance-matrix.md), `PUBLIC_SEPOLIA_DEPLOY.md`), and paper-safe execution with optional Kraken market ingestion — it is *not* ‘fully ERC-8004 compliant’ under the draft as a whole and does not ship a protocol-mandated canonical mainnet registry.”**

**Do not say:** “ERC-8004 compliant,” “fully on-chain,” “domain verified in the CA/PKI sense,” or “registered on the official global ERC-8004 registry” unless those statements are strictly true for your deployment.
