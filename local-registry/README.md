# VeriTrade local ERC-8004-style registries (Anvil / dev chain only)

Solidity contracts for **local developer chains** (Anvil, Hardhat, etc.). They are **not** production deployments, **not** audited, and **not** normative EIP-8004 reference implementations. They exist so judges and developers can run **real** `register`, `validationRequest` / `validationResponse`, `giveFeedback`, and **ERC-1271** checks with inspectable logs.

Canonical interface stubs remain in `../spec-alignment/contracts/`; this folder vendors copies under `src/interfaces/` so `forge build` is self-contained.

## First-time setup (dependencies)

`forge-std` and OpenZeppelin are **not** committed under `lib/` (gitignored). Install once:

**Linux / macOS** (from repo root):

```bash
bash scripts/erc8004/forge-bootstrap.sh
```

**Windows** (from repo root):

```powershell
pwsh scripts/erc8004/forge-bootstrap.ps1
```

Or manually:

```bash
cd local-registry
forge install foundry-rs/forge-std@v1.9.4 --no-git
forge install OpenZeppelin/openzeppelin-contracts@v5.0.2 --no-git
forge build
forge test -vvv
```

## Prerequisites

- [Foundry](https://book.getfoundry.sh/getting-started/installation) (`forge`, `cast`, `anvil`)

## Build & test

```bash
cd local-registry
forge build
forge test -vvv
```

CI: `.github/workflows/contracts.yml` runs `forge build` + `forge test` on every change under `local-registry/`.

## One-shot **compliance evidence** bundle (deploy + mint + validation + reputation)

Terminal A: `anvil` (use another `--port` if `8545` is busy).

Terminal B:

```bash
cd local-registry
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
forge script script/LocalProofBundle.s.sol:LocalProofBundle --rpc-url http://127.0.0.1:8545 --broadcast --sig "run()" -vvvv
```

Writes **`evidence/latest-local-proof.json`** (gitignored) with addresses and the `validation_request_hash` used in the walkthrough. See **`../docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md`** and **`../docs/erc8004-compliance-matrix.md`**.

## One-shot deploy (broadcast all four contracts only)

Terminal A: `anvil`

Terminal B:

```bash
cd local-registry
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
forge script script/DeployAll.s.sol:DeployAll --rpc-url http://127.0.0.1:8545 --broadcast --sig "run()" -vvvv
```

The script deploys, in order:

1. `VeriTradeLocalIdentityRegistry`
2. `VeriTradeEip1271IntentAdapter` with **owner = deployer** (use deployer key for EIP-712 when using this script alone)
3. `VeriTradeLocalValidationRegistry`
4. `VeriTradeLocalReputationRegistry`

**Note:** `LocalProofBundle.s.sol` uses **agent-owned** adapter (Anvil **#1**) and **validator** (**#2**) for validation/reputation — prefer that path for judge demos; see `docs/evidence/ANVIL_WALLET_ROLES.md`.

## Manual `forge create` (alternative)

See previous revision of this README in git history, or use `cast`/`forge create` per contract with `--constructor-args` for registries that need the identity address.

## Mint an agent identity (`register`)

Pick your hosted registration URL (for example `http://127.0.0.1:34120/challenge/agent-registration` while the API is running):

```bash
cast send $IDENTITY "register(string)(uint256)" "http://127.0.0.1:34120/challenge/agent-registration" --rpc-url http://127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

Read `Registered` in logs; first `agentId` is usually `1`.

### Ownership

- `setAgentURI` and `transferAgentOwnership` are **owner-gated** (`msg.sender == ownerOf[agentId]`).

## Validation Registry — important: who may respond?

`validationResponse` **must** be sent from the **same address** passed as `validatorAddress` in `validationRequest`. The contract enforces `msg.sender == validatorAddress`.

Example (bash; use **validator** key for the response tx):

```bash
export VAL=0x... # VeriTradeLocalValidationRegistry
export REQHASH=0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
cast send $VAL "validationRequest(address,uint256,string,bytes32)" \
  0x0000000000000000000000000000000000000B01 1 "http://127.0.0.1:34120/challenge/erc8004-shapes" $REQHASH \
  --rpc-url http://127.0.0.1:8545 --private-key 0xac0974...

# Use the validator key (here 0x...0B01's private key — only for local demos):
cast send $VAL "validationResponse(bytes32,uint8,string,bytes32,string)" \
  $REQHASH 85 "ipfs://example/response.json" 0x0000000000000000000000000000000000000000000000000000000000000000 "demo" \
  --rpc-url http://127.0.0.1:8545 --private-key <VALIDATOR_PRIVATE_KEY>
```

## Reputation `giveFeedback` / `revokeFeedback`

`revokeFeedback` requires `feedbackIndex` to be **less than** the number of feedback entries the client has already submitted for that `agentId`.

## Bridge scripts (Python → on-chain txs)

From repo root (requires `web3` and API `app` on path — scripts self-adjust `PYTHONPATH`):

**validationRequest**

```bash
python scripts/erc8004/post_validation_request.py \
  --rpc http://127.0.0.1:8545 \
  --private-key 0xac0974... \
  --registry 0xYourValidationRegistry \
  --validator 0x0000000000000000000000000000000000000B01 \
  --agent-id 1 \
  --request-uri https://example/req.json \
  --payload-json-file spec-alignment/schemas/validation-request.example.json
```

**validationResponse** (caller must be the validator address from the request)

```bash
python scripts/erc8004/post_validation_response.py \
  --rpc http://127.0.0.1:8545 \
  --private-key <VALIDATOR_KEY> \
  --registry 0xYourValidationRegistry \
  --request-hash 0x... \
  --response 85 \
  --response-uri ipfs://... \
  --response-hash 0x0000000000000000000000000000000000000000000000000000000000000000 \
  --tag demo
```

**giveFeedback**

```bash
python scripts/erc8004/post_reputation_feedback.py \
  --rpc http://127.0.0.1:8545 \
  --private-key 0xac0974... \
  --registry 0xYourReputationRegistry \
  --agent-id 1
```

## Bind VeriTrade `.env` after mint

Set (see root `.env.example`):

- `ERC8004_IDENTITY_REGISTRY_ADDRESS`
- `ERC8004_ONCHAIN_AGENT_ID` (decimal token id, usually `1` on first mint)
- `ERC8004_VALIDATION_REGISTRY_ADDRESS` / `ERC8004_REPUTATION_REGISTRY_ADDRESS` (optional)
- `ERC8004_DEV_CHAIN_ID` (e.g. `31337` for Anvil)
- `ERC8004_RPC_URL` (optional; enables ERC-1271 `eth_call` in `GET /intents/{id}/signature-verification`)
- `VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT` = deployed `VeriTradeEip1271IntentAdapter` when using the adapter path
- `VERITRADE_INTENT_SIGNER_PRIVATE_KEY` = **same** key as adapter `owner` (deployer) for local demos

Then `GET /challenge/agent-registration` fills `registrations[]`. Sync static web copy: `python scripts/export_agent_registration_static.py` (repo root).

## Public **Ethereum Sepolia** (operator-funded; HTTPS `/.well-known`)

VeriTrade ships **`script/SepoliaDeployAndMint.s.sol`** plus **`../scripts/erc8004/deploy_sepolia.sh`** (or `.ps1`) to deploy the same four contracts on **Sepolia** and `register(PUBLIC_AGENT_REGISTRATION_URL)` with a real HTTPS agent registration URL.

**Read first:** [`../docs/evidence/PUBLIC_SEPOLIA_DEPLOY.md`](../docs/evidence/PUBLIC_SEPOLIA_DEPLOY.md) and [`../docs/deployment/VERCEL_WEB.md`](../docs/deployment/VERCEL_WEB.md).

This does **not** create a protocol-mandated “canonical” mainnet registry — it is an **operator-owned** testnet deployment path for public evidence.

**Anvil-only** workflows (`LocalProofBundle`, `DeployAll`) above are **unchanged**.
