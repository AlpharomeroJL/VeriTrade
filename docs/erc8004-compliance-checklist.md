# ERC-8004 (draft) — VeriTrade compliance checklist

**Authoritative requirement-by-requirement matrix (with proof links):** [erc8004-compliance-matrix.md](erc8004-compliance-matrix.md).

Normative reference: [EIP-8004: Trustless Agents (DRAFT)](https://eips.ethereum.org/EIPS/eip-8004). This checklist maps **draft expectations** to **VeriTrade implementation status**. It is a **truth instrument**, not a self-certification of “full compliance.”

## Legend

| Tag | Meaning |
|-----|---------|
| **implemented** | Behavior exists, exercised by automated tests or scripted flows in-repo. |
| **partial** | Subset implemented; gaps called out in-row. |
| **local/testnet only** | Real on-chain style behavior on Anvil / chosen testnet only; not public mainnet. |
| **off-chain / protocol-shaped** | JSON, hashes, or API surfaces aligned to draft narrative; not a chain transaction. |
| **deferred** | Explicitly out of scope for current codebase or blocked (audits, production ops, etc.). |

---

## Identity Registry

| Draft expectation (summary) | Status | Notes |
|----------------------------|--------|--------|
| Mint / register agent identity | **local/testnet only** | `local-registry/src/VeriTradeLocalIdentityRegistry.sol` — `register(uri)` returns `agentId`, emits `Registered`. |
| `agentURI` storage + update | **local/testnet only** | `agentURI(uint256)` view; `setAgentURI` owner-gated; emits `URIUpdated`. |
| Ownership / transfer | **partial** | `transferAgentOwnership` added for local registry; **not** full ERC-721 compatibility. |
| Metadata entries (`setMetadata` / `getMetadata`) | **local/testnet only** | `VeriTradeLocalIdentityRegistry` string KV (key hashed); tests + `LocalProofBundle` sets `agentWallet`; optional `GET .../onchain-read?identity_metadata_key=`. |
| `agentWallet` + EIP-712 wallet update flows | **partial** + **local/testnet only** | On-chain `agentWallet` / `walletNonce`, owner + EIP-712 signed updates (`VeriTradeLocalIdentityRegistry`); Python typed-data helper. Still **not** a production global identity service. |

---

## Registration file (`agentURI` target)

| Draft expectation | Status | Notes |
|------------------|--------|--------|
| `type`, `name`, `description`, `image`, `services` | **implemented** | `build_agent_registration()` + template. |
| `registrations[]` with `agentRegistry` + `agentId` (+ `agentURI`) | **partial** | Filled when `ERC8004_IDENTITY_REGISTRY_ADDRESS` + `ERC8004_ONCHAIN_AGENT_ID` set after **your** mint. |
| `supportedTrust` | **implemented** | From template; values are **claims of intent**, not on-chain proof. |
| Static `.well-known` copy synced to API | **partial** | `scripts/export_agent_registration_static.py`; static file can drift until run. |

---

## Endpoint / domain verification (draft optional)

| Draft expectation | Status | Notes |
|------------------|--------|--------|
| Same-origin / fetch checks | **implemented** | `GET /challenge/agent-registration/verify` — **no** CA/PKI guarantee. |
| HTTPS-only / DNSSEC proof | **deferred** | Not implemented; would be ops / hosting outside this repo. |

---

## Validation Registry

| Draft expectation | Status | Notes |
|------------------|--------|--------|
| `validationRequest` + event | **local/testnet only** | Local contract implements `IValidationRegistry`; emits `ValidationRequest`. |
| `validationResponse` + event | **local/testnet only** | Emits `ValidationResponse`; **only** `validatorAddress` from the matching `validationRequest` may call `validationResponse` (`msg.sender` check). |
| `requestHash` / `responseHash` semantics | **partial** | On-chain: opaque `bytes32`; off-chain: `keccak256(canonical JSON)` helper in Python for artifacts. |
| `getValidationStatus` | **local/testnet only** | Implemented in local contract. |
| Automatic bridge from VeriTrade DB artifacts → chain | **deferred** | **Not** wired into pipeline; optional `post_validation_request.py` or `post_validation_from_artifact.py` (`--dry-run` or forward). |

---

## Reputation Registry

| Draft expectation | Status | Notes |
|------------------|--------|--------|
| `giveFeedback` + `NewFeedback` event | **local/testnet only** | Local contract implements interface subset. |
| `FeedbackRevoked` | **partial** | Emitted with **bounds check** on `feedbackIndex`; no persisted revocation table (minimal). |
| Read / aggregate scores | **partial** | On-chain: `feedbackCount(client, agentId)` + API `onchain-read`; no score aggregation or payload replay. |

---

## Typed data / wallets (intents + ERC-1271)

| Draft expectation | Status | Notes |
|------------------|--------|--------|
| EIP-712 typed trade intent | **implemented** | `app/challenge/eip712_intent.py`; persisted on `TradeIntent` when signer env set. |
| Sign + recover (EOA) | **implemented** | `eth-account`; tests cover round-trip. |
| Chain-aware domain (`chainId`, `verifyingContract`) | **implemented** | From `Settings`. |
| ERC-1271 `isValidSignature` for contract “verifying” wallet | **partial** | Primary adapter + optional **second** verifier address (`VERITRADE_EIP1271_SECONDARY_VERIFIER`) via same `eth_call` helper. **Not** a universal smart-wallet matrix. |
| Full smart-wallet / Safe / universal verifier | **deferred** | Out of scope; document blockers in `docs/intent-envelope.md`. |

---

## Tooling & reproducibility

| Item | Status | Notes |
|------|--------|--------|
| `forge build` / `forge test` | **implemented** | After `scripts/erc8004/forge-bootstrap.*` installs `lib/` deps. CI: `.github/workflows/contracts.yml`. Includes `testComplianceEvidence_identityValidationReputationChain`. |
| One-shot deploy script | **implemented** | `local-registry/script/DeployAll.s.sol` (Foundry `script`). |
| One-shot local proof bundle | **implemented** | `local-registry/script/LocalProofBundle.s.sol` → `evidence/latest-local-proof.json`; walkthrough `docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md`. |
| Bridge scripts (validation + reputation) | **implemented** | `post_validation_request.py`, `post_validation_response.py`, `post_reputation_feedback.py` — optional RPC + key. |
| API read of `getValidationStatus` / `feedbackCount` / `getMetadata` | **implemented** | `GET /challenge/erc8004/onchain-read` (+ query params; see matrix). |
| Anvil wallet role map | **implemented** | `docs/evidence/ANVIL_WALLET_ROLES.md`, `.env.anvil.example`, `print_anvil_roles.py`, `prove_local_slice.*` |
| Public **Sepolia** deploy + mint | **partial** | `SepoliaDeployAndMint.s.sol`, `deploy_sepolia.*`, `PUBLIC_SEPOLIA_DEPLOY.md` — **requires** operator-funded key + live HTTPS URL; evidence JSON gitignored. |

---

## Target vs achieved (this pass)

| Area | Target for this pass | Achieved |
|------|---------------------|----------|
| Identity | Runnable mint + URI + binding | **Yes** (local), + ownership transfer |
| Registration | Env-bound `registrations[]` | **Yes** |
| Validation | Runnable request/response + hashes | **Yes** (local), validator-only response |
| Reputation | Runnable feedback + events | **Yes** (local), minimal revoke |
| EIP-712 | Real sign + verify + digest for 1271 | **Yes** |
| ERC-1271 | Feasible minimal path | **Yes** (adapter + optional second verifier + off-chain verify helper) |
| Auto on-chain from trading loop | Nice-to-have | **Partial** (opt-in artifact bridge + scripts; default off) |
| Public Sepolia + HTTPS `/.well-known` | Operator public proof | **Partial** (Foundry script + docs + Vercel guide; **requires** funded key + deploy) |
