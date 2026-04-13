# ERC-8004 local compliance proof — reproducible walkthrough

This is a **judge/developer** procedure to reproduce **on-chain evidence** for VeriTrade’s optional `local-registry` contracts (Anvil / dev chain). It does **not** assert mainnet ERC-8004 compliance.

Normative draft: [EIP-8004](https://eips.ethereum.org/EIPS/eip-8004).

## Preconditions

- Foundry (`forge`, `cast`, `anvil`) on `PATH`
- From repo root once: `bash scripts/erc8004/forge-bootstrap.sh` or `pwsh scripts/erc8004/forge-bootstrap.ps1` (installs `lib/`)
- **Wallet roles:** see [ANVIL_WALLET_ROLES.md](ANVIL_WALLET_ROLES.md) and repo [`.env.anvil.example`](../../.env.anvil.example). Print defaults: `python scripts/erc8004/print_anvil_roles.py`

## Fastest “prove it” slice (unit test + role map; no Anvil)

```bash
# repo root
bash scripts/erc8004/prove_local_slice.sh
# or: pwsh scripts/erc8004/prove_local_slice.ps1
```

## One terminal — Anvil

Use a free port if `8545` is busy (Windows example uses `18545`):

```bash
anvil --port 8545
```

## Second terminal — full chain walk (deploy + mint + validation + reputation)

```bash
cd local-registry
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
forge script script/LocalProofBundle.s.sol:LocalProofBundle \
  --rpc-url http://127.0.0.1:8545 \
  --broadcast \
  --sig "run()" \
  -vvvv
```

**Artifacts**

- `local-registry/evidence/latest-local-proof.json` — addresses, `agent_id`, `validation_request_hash`, etc.
- `local-registry/broadcast/LocalProofBundle.s.sol/<chainId>/run-latest.json` — broadcast receipts (gitignored under `broadcast/`).

## Third terminal — Forge unit evidence (no Anvil required)

```bash
cd local-registry
forge test -vvv --match-test testComplianceEvidence_identityValidationReputationChain
```

## Bind the API (optional)

Copy the `NEXT_BIND_ENV` lines from the forge script logs into the API `.env` (use the **same** `--rpc-url` value for `ERC8004_RPC_URL`).

Then:

1. Start API + web; run `python scripts/export_agent_registration_static.py` so `/.well-known` matches `GET /challenge/agent-registration`.
2. `GET /challenge/agent-registration/verify` — same-host / fetch / env-binding report.
3. `GET /challenge/erc8004/onchain-read?validation_request_hash=<from evidence JSON>` — `getValidationStatus`.
4. Same route (with identity + RPC): response includes **`agent_wallet`** / **`wallet_nonce`** when the deployed `VeriTradeLocalIdentityRegistry` supports them.
5. Optional: `&identity_metadata_key=agentWallet` — `getMetadata`; `&reputation_client_address=<validator>` — `feedbackCount`; `&reputation_feedback_index=0` — **`getFeedback`** (requires reputation registry + onchain agent id).

## Typed intent + ERC-1271 (optional dev path)

When `VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT` is the deployed `VeriTradeEip1271IntentAdapter` and the signer key matches the adapter **owner** (**agent** = Anvil account **#1** after `LocalProofBundle`), new trade intents get EIP-712 signatures. With `ERC8004_RPC_URL` set, `GET /intents/{id}/signature-verification` performs **EOA recover** and optional **ERC-1271 `eth_call`**. Set **`VERITRADE_EIP1271_SECONDARY_VERIFIER`** to a second contract address to repeat the same `isValidSignature` probe — still **not** a universal Safe / smart-wallet integration.

## Identity `agentWallet` (on-chain + EIP-712)

After `LocalProofBundle`, the agent calls **`setAgentWalletAsOwner`** so `agentWallet(agentId)` matches the agent EOA. For wallet rotation demos, integrators can sign **`SetAgentWallet`** using `identity_wallet_eip712.build_set_agent_wallet_typed_data` and submit **`setAgentWalletWithSig`** on-chain (see `test/Registry.t.sol`).

## Optional: artifact → `validationRequest` (API)

When **`ERC8004_ARTIFACT_VALIDATION_EMIT_ENABLED=true`** and RPC / registry / validator / private key / on-chain agent id are set, writing artifacts of types in **`ERC8004_ARTIFACT_VALIDATION_TRIGGER_TYPES`** (default `execution,lane_execution`) may emit a **`validationRequest`**. Failures are logged only — artifact persistence is unchanged.

## Bridge validation request from a VeriTrade-shaped JSON file

```bash
python scripts/erc8004/post_validation_request.py \
  --rpc http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --registry <VALIDATION_REGISTRY_FROM_EVIDENCE_JSON> \
  --validator 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
  --agent-id 1 \
  --request-uri http://127.0.0.1:34120/challenge/erc8004-shapes \
  --payload-json-file spec-alignment/schemas/validation-request.example.json
```

Validator response (must use **validator** private key):

```bash
python scripts/erc8004/post_validation_response.py \
  --rpc http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --registry <VALIDATION_REGISTRY> \
  --request-hash <REQUEST_HASH_FROM_POST_OR_LOGS> \
  --response 85 \
  --response-uri ipfs://example/response.json \
  --response-hash 0x0000000000000000000000000000000000000000000000000000000000000000 \
  --tag demo
```

Reputation feedback:

```bash
python scripts/erc8004/post_reputation_feedback.py \
  --rpc http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --registry <REPUTATION_REGISTRY> \
  --agent-id 1
```

## PowerShell (Windows) equivalents

Use `$env:PRIVATE_KEY="0xac0..."` and `forge script ... --rpc-url http://127.0.0.1:8545` as above. If `anvil` fails with “address already in use”, pick another `--port` and pass the same port to `--rpc-url`.

See also: `scripts/erc8004/local_compliance_proof.ps1` (prints this sequence).

## Public Ethereum Sepolia (separate from Anvil)

Operator-funded deploy + HTTPS `/.well-known` binding: **[PUBLIC_SEPOLIA_DEPLOY.md](PUBLIC_SEPOLIA_DEPLOY.md)** and **`local-registry/script/SepoliaDeployAndMint.s.sol`**. Does **not** replace the Anvil walkthrough above.
