# ERC-8004 (draft) — VeriTrade compliance matrix (evidence spine)

**Normative reference:** [EIP-8004: Trustless Agents (DRAFT)](https://eips.ethereum.org/EIPS/eip-8004).

This matrix is the **single requirement-by-requirement** map for this pass. Status vocabulary:

| Status | Meaning |
|--------|---------|
| **implemented + proven** | Code exists and is exercised by automated tests and/or scripted local-chain flow with named artifacts. |
| **implemented + partial** | Subset only; gap named in-row. |
| **local/testnet only** | Real EVM txs/events on Anvil or operator-chosen testnet; **not** a mainnet canonical registry deployment. |
| **off-chain / API only** | JSON-RPC read, HTTP surfaces, hashes — no required chain tx in default app loop. |
| **not implemented** | Missing relative to draft expectation for this row. |
| **out of scope** | Explicitly excluded (production PKI, full smart-wallet product, etc.). |

**Verdict (evidence-backed):** VeriTrade is **not** “fully ERC-8004 compliant” in the normative sense. It provides **draft-aligned** surfaces plus **reproducible proof** on **Anvil** and, when an operator funds it, on **public Sepolia** using the same local-registry contracts + HTTPS `/.well-known` registration. See **§ Remaining blockers** at the end.

---

## 1. Identity Registry

| ID | Draft-oriented requirement | Status | Proof |
|----|---------------------------|--------|-------|
| I1 | Register agent; receive `agentId`; emit registration-shaped event | **local/testnet only** | Contract: `local-registry/src/VeriTradeLocalIdentityRegistry.sol` (`register`, `Registered`). Test: `test/Registry.t.sol` → `testIdentity_register_setURI_transfer`, `testComplianceEvidence_identityValidationReputationChain`. Script: `local-registry/script/LocalProofBundle.s.sol` (mint in `run()`). |
| I2 | `agentURI` readable; owner may update URI | **local/testnet only** | `agentURI`, `setAgentURI`, `URIUpdated`. Test: `testIdentity_register_setURI_transfer`. |
| I3 | Ownership / transfer semantics | **implemented + partial** | `transferAgentOwnership` (not full ERC-721). Same tests as I1. |
| I4 | Existence query | **local/testnet only** | `exists(uint256)`. Test: `testIdentity_register_setURI_transfer`. |
| I5 | On-chain metadata KV (`setMetadata` / `getMetadata`) | **local/testnet only** | `VeriTradeLocalIdentityRegistry`: string map keyed by `keccak256(key)`, owner-gated; `MetadataUpdated` event. Tests: `test/Registry.t.sol::testIdentity_setMetadata_getMetadata_ownerOnly`. `LocalProofBundle` sets `agentWallet` metadata. Read: `GET /challenge/erc8004/onchain-read?identity_metadata_key=agentWallet` (+ RPC + identity env). |
| I6 | `agentWallet` + EIP-712 wallet-update flows per draft | **local/testnet only** + **implemented + partial** | On-chain **`agentWallet` / `walletNonce`**; **`setAgentWalletAsOwner`**; **`setAgentWalletWithSig`** (EIP-712 via OZ `EIP712` + `ECDSA`; signer = owner or current wallet); view **`digestSetAgentWallet`** for integrators. Contract/tests: `VeriTradeLocalIdentityRegistry.sol`, `testIdentity_setAgentWalletAsOwner_advancesNonce`, `testIdentity_setAgentWalletWithSig_*`. Off-chain typed data: `apps/api/app/challenge/identity_wallet_eip712.py`. **`LocalProofBundle`** calls `setAgentWalletAsOwner` after mint. Optional metadata `agentWallet` string + registration placeholder unchanged. **Gap:** local demo semantics only; not a normative global registry / audited rotation service. |

---

## 2. Agent registration file (`agentURI` target)

| ID | Draft-oriented requirement | Status | Proof |
|----|---------------------------|--------|-------|
| R1 | `type`, `name`, `description`, `image`, `services` | **implemented + proven** | Template: `spec-alignment/agent-registration.json`. Builder: `apps/api/app/challenge/registration.py` → `GET /challenge/agent-registration`. Test: `tests/test_erc8004_alignment.py::test_agent_registration_matches_eip_type`. |
| R2 | Static `.well-known` JSON | **implemented + partial** | `apps/web/public/.well-known/agent-registration.json` + **`apps/web/vercel.json`** (SPA fallback; `public/` served first on Vercel). Align with API via `python scripts/export_agent_registration_static.py`. [docs/deployment/VERCEL_WEB.md](../deployment/VERCEL_WEB.md). |
| R3 | `registrations[]` binds `agentRegistry` + `agentId` (+ optional `agentURI`) | **local/testnet only** + **off-chain** | Filled when env set after mint: `registration.py`; test `test_agent_registration_env_registry_binding`. On-chain URI set in `LocalProofBundle.s.sol`. Optional **`agentWallet`** in served JSON when `VERITRADE_AGENT_WALLET_PLACEHOLDER` set (truthful string; verify on-chain via metadata read if desired). |
| R4 | `supportedTrust` truthful | **implemented + proven** | Template lists intent-level trust modes; **not** cryptographic proof of trust. Same template + API. |
| R5 | `x402Support` / `active` fields | **implemented + proven** | Present in template + served JSON. |

---

## 3. Endpoint / domain verification

| ID | Draft-oriented requirement | Status | Proof |
|----|---------------------------|--------|-------|
| E1 | Same-host / fetch comparison for registration JSON | **implemented + proven** | `apps/api/app/challenge/registration_verify.py` → `GET /challenge/agent-registration/verify`. Test: `test_challenge_agent_registration_verify_route`. |
| E2 | CA-trusted HTTPS / DNSSEC / production domain control | **out of scope** | Explicitly **not** claimed; notes in verify response. |

---

## 4. Validation Registry

| ID | Draft-oriented requirement | Status | Proof |
|----|---------------------------|--------|-------|
| V1 | `validationRequest` + `ValidationRequest` event | **local/testnet only** | `local-registry/src/VeriTradeLocalValidationRegistry.sol`. Tests: `testValidation_onlyValidatorMayRespond`, `testComplianceEvidence_identityValidationReputationChain`. |
| V2 | `validationResponse` + `ValidationResponse` event | **local/testnet only** | Same contract; validator-only `msg.sender` check. Same tests. |
| V3 | `requestHash` / `responseHash` as opaque commitments | **implemented + partial** | On-chain: `bytes32`. Off-chain canonical JSON → keccak: `apps/api/app/challenge/erc8004_validation.py` (`validation_request_hash_from_canonical_payload`). Script: `scripts/erc8004/post_validation_request.py`. |
| V4 | `getValidationStatus` read path | **local/testnet only** + **off-chain** | Contract view + `onchain_registry.py` → `GET /challenge/erc8004/onchain-read?validation_request_hash=0x…` when `ERC8004_RPC_URL` + validation registry env set. Optional same-route: `reputation_client_address` + reputation registry + onchain agent id → `feedbackCount`; `identity_metadata_key` → `getMetadata`. |
| V5 | Automatic post from trading loop | **implemented + partial** | Default: **no** auto-post (stability). Optional **`scripts/erc8004/post_validation_from_artifact.py`** (`--dry-run` or forward to `post_validation_request.py`) for file-driven requests. |
| V6 | End-to-end local deploy + request + response (+ reputation + metadata) | **implemented + proven** | `script/LocalProofBundle.s.sol` (multi-role: deployer / agent / validator) + walkthrough + `docs/evidence/sample-local-proof-bundle.json` + `ANVIL_WALLET_ROLES.md`. |

---

## 5. Reputation Registry

| ID | Draft-oriented requirement | Status | Proof |
|----|---------------------------|--------|-------|
| P1 | `giveFeedback` + `NewFeedback` event | **local/testnet only** | `local-registry/src/VeriTradeLocalReputationRegistry.sol`. Test: `testComplianceEvidence_identityValidationReputationChain`. Script: `scripts/erc8004/post_reputation_feedback.py`. |
| P2 | `revokeFeedback` + `FeedbackRevoked` | **implemented + partial** | Index bounds only; no persisted revocation bitmap. Test: `testReputation_revokeRequiresIssuedIndex`. |
| P3 | On-chain read / aggregate summaries | **implemented + partial** | **`feedbackCount`** + **`getFeedback(client, agentId, index)`** (persisted payloads). Tests: `testReputation_feedbackCountTracksIssued`, `testReputation_getFeedback_roundTrip`. API: `onchain-read` + `reputation_feedback_index`. **No** cross-client aggregation / Sybil resistance. |

---

## 6. Typed signing (EIP-712) & wallet flows

| ID | Draft-oriented requirement | Status | Proof |
|----|---------------------------|--------|-------|
| T1 | Typed trade-intent domain + digest | **implemented + proven** | `apps/api/app/challenge/eip712_intent.py`. Tests: `tests/test_eip712_intent.py` (digest stability, signing configured). |
| T2 | Sign + recover (EOA) | **implemented + proven** | `apps/api/app/services/intent_service.py` + `verify_trade_intent_typed_data`; route `GET /intents/{id}/signature-verification`. Integration: `tests/test_integration_flow.py`. |
| T3 | Chain-aware domain (`chainId`, `verifyingContract`) | **implemented + proven** | `Settings.erc8004_dev_chain_id`, `veritrade_intent_eip712_verifying_contract`. |
| T4 | Full smart-wallet / Safe / universal verifier | **not implemented** | See `docs/intent-envelope.md`; only adapter path below. |

---

## 7. ERC-1271

| ID | Draft-oriented requirement | Status | Proof |
|----|---------------------------|--------|-------|
| K1 | Contract `isValidSignature` for a **designated** “verifying contract” | **implemented + partial** | `VeriTradeEip1271IntentAdapter.sol` — owner ECDSA; magic `0x1626ba7e` or **`0xffffffff`** per ERC-1271 failure idiom. Tests: `testEip1271_magicValueForOwnerSignature`, `testEip1271_wrongSignerReturnsInvalidMagic`. |
| K2 | Off-chain verification via `eth_call` | **off-chain / API only** | `apps/api/app/challenge/eip1271_intent.py`; used from `GET /intents/{id}/signature-verification` when `ERC8004_RPC_URL` set. |
| K3 | Generic ERC-1271 for arbitrary smart wallets | **implemented + partial** | Same wire **`isValidSignature(bytes32,bytes)`** helper `verify_eip1271_is_valid_signature` for an **optional second** address via `VERITRADE_EIP1271_SECONDARY_VERIFIER` on `GET /intents/{id}/signature-verification` → `eip1271_secondary_eth_call`. **Not** a universal Safe / smart-wallet verifier product; still contract-specific semantics per callee. |

---

## 8. Tooling, CI, reproducibility

| ID | Requirement | Status | Proof |
|----|-------------|--------|-------|
| X1 | `forge build` / `forge test` | **implemented + proven** | `local-registry/`; CI: `.github/workflows/contracts.yml`. |
| X2 | One-shot deploy | **implemented + proven** | `local-registry/script/DeployAll.s.sol`. |
| X3 | One-shot **full slice** (deploy + mint + validation + reputation + evidence JSON) | **implemented + proven** | `local-registry/script/LocalProofBundle.s.sol` → `local-registry/evidence/latest-local-proof.json` (gitignored json; committed sample shape: `docs/evidence/sample-local-proof-bundle.json`). |
| X4 | Helper scripts | **implemented + proven** | `forge-bootstrap.*`, `post_validation_request.py`, `post_validation_response.py`, `post_reputation_feedback.py`, **`post_validation_from_artifact.py`**, **`erc8004_artifact_validation_bridge.py`** (runtime opt-in), `local_compliance_proof.*`, **`print_anvil_roles.py`**, **`prove_local_slice.ps1` / `.sh`**, **`deploy_sepolia.sh` / `.ps1`**. |
| X5 | Public **Ethereum Sepolia** deploy + mint + evidence JSON | **implemented + partial** | **`script/SepoliaDeployAndMint.s.sol`** + **[PUBLIC_SEPOLIA_DEPLOY.md](evidence/PUBLIC_SEPOLIA_DEPLOY.md)** + **[sepolia-public-proof.example.json](evidence/sepolia-public-proof.example.json)**. **Requires** operator-funded keys + real `PUBLIC_AGENT_REGISTRATION_URL`; output **`evidence/sepolia-public-proof.json`** (gitignored). **Not** a protocol-mandated canonical mainnet registry. |
| W1 | Local Anvil wallet / role mapping | **implemented + proven** | **`docs/evidence/ANVIL_WALLET_ROLES.md`**, **`.env.anvil.example`**, `print_anvil_roles.py`. `LocalProofBundle` uses deployer / agent / validator keys (`PRIVATE_KEY`, optional `AGENT_PRIVATE_KEY`, `VALIDATOR_PRIVATE_KEY`). |

---

## Remaining blockers (prevent a truthful “fully ERC-8004 compliant” claim)

1. **No protocol-mandated “official” mainnet ERC-8004 registry** — Sepolia (or other testnet) deployments are **VeriTrade-operator-owned** contracts documented in-repo, **not** a global canonical registry ID baked into the EIP.
2. **Identity / validation / reputation** remain **minimal local-registry semantics** (demo-shaped), not a full audited production registry product.
3. **Validation** on-chain emission from the core trading loop is still **opt-in / env-gated** by default.
4. **Reputation** lacks cross-client aggregation, Sybil resistance, and normative “score” semantics.
5. **ERC-1271** coverage is **bounded** (adapter + optional second verifier `eth_call`), not a universal smart-wallet matrix.
6. **Endpoint / TLS** checks are **honest transparency** (fetch, same-origin, runtime TLS observation, `agentURI` document fetch) — **not** Web PKI attestation or DNSSEC proof.

---

## Final answers (required)

| Question | Answer |
|----------|--------|
| Is VeriTrade fully ERC-8004 compliant? | **No.** |
| If no, what blocks that? | **§ Remaining blockers** above plus any row still **implemented + partial** vs a normative “full protocol” bar. |
| What proves the strongest truthful claim? | **Anvil:** `LocalProofBundle`, Foundry tests, local walkthrough. **Public testnet (operator-run):** `SepoliaDeployAndMint` + `PUBLIC_SEPOLIA_DEPLOY.md` + `evidence/sepolia-public-proof.json` + bound `/.well-known` + `verify` / `onchain-read` — cited in-row. |
