# Public Sepolia deployment — VeriTrade local-registry + HTTPS registration

This document is the **operator runbook** for closing the **“no public/shared on-chain deployment”** gap using **Ethereum Sepolia** (free public testnet, chain ID **11155111**), **Foundry**, and a **public HTTPS** agent registration file at **`/.well-known/agent-registration.json`** (e.g. Vercel-hosted web app).

**Truth labels**

- This deploys **VeriTrade’s own bytecode** on Sepolia — **not** an “official” global ERC-8004 registry mandated by the draft.
- Live **contract addresses and tx hashes** live in **your** `local-registry/broadcast/…` tree and **`evidence/sepolia-public-proof.json`** after you run the script — **do not** expect those secrets/addresses to be committed to git.
- VeriTrade remains **not** “fully ERC-8004 compliant” in the normative sense; see [erc8004-compliance-matrix.md](../erc8004-compliance-matrix.md).

## Why Sepolia

- **Public JSON-RPC** (e.g. `https://ethereum-sepolia.publicnode.com`, Alchemy/Infura free tiers).
- **Foundry** `forge script --broadcast` works unchanged.
- **Faucets** are widely available for test ETH (search “Sepolia faucet”).
- **Chain ID** `11155111` is stable for `ERC8004_DEV_CHAIN_ID` in production `.env`.

## Prerequisites

1. [Foundry](https://book.getfoundry.sh/) installed; `local-registry` dependencies bootstrapped (`scripts/erc8004/forge-bootstrap.sh` or `.ps1`).
2. A **Sepolia-funded** EOA private key (`PRIVATE_KEY`). Optionally a separate **`AGENT_PRIVATE_KEY`** (defaults to `PRIVATE_KEY` if unset).
3. **Vercel (or other HTTPS host)** for the **web** app so this URL is real **before** minting:

   `PUBLIC_AGENT_REGISTRATION_URL=https://<your-domain>/.well-known/agent-registration.json`

4. **Order of operations (important):**
   - Deploy **web** to Vercel with **Root Directory** = `apps/web` (see [VERCEL_WEB.md](../deployment/VERCEL_WEB.md)).
   - Point **`VERITRADE_WEB_BASE_URL`** and **`VERITRADE_API_BASE_URL`** in the API host’s `.env` to the **public** URLs.
   - Set registry env vars **after** on-chain deploy (next section), then run **`python scripts/export_agent_registration_static.py`** so the **static** JSON matches `GET /challenge/agent-registration`.
   - Run **`SepoliaDeployAndMint`** with `PUBLIC_AGENT_REGISTRATION_URL` equal to that **HTTPS** `/.well-known/...` URL so **`register(uri)`** matches what validators/users fetch.

## Deploy contracts + mint agent

From repo root (bash):

```bash
export PRIVATE_KEY=0x...          # funded Sepolia deployer
# optional: export AGENT_PRIVATE_KEY=0x...
export PUBLIC_AGENT_REGISTRATION_URL='https://YOUR_DOMAIN/.well-known/agent-registration.json'
# optional: export SEPOLIA_RPC_URL='https://ethereum-sepolia.publicnode.com'

bash scripts/erc8004/deploy_sepolia.sh
```

Windows:

```powershell
$env:PRIVATE_KEY="0x..."
$env:PUBLIC_AGENT_REGISTRATION_URL="https://YOUR_DOMAIN/.well-known/agent-registration.json"
pwsh scripts/erc8004/deploy_sepolia.ps1
```

**Artifacts**

- `local-registry/evidence/sepolia-public-proof.json` (gitignored) — addresses + `agent_id` + `agent_uri_on_chain`.
- `local-registry/broadcast/SepoliaDeployAndMint.s.sol/11155111/run-latest.json` — broadcast receipts (Foundry default).

## Bind the API / static registration

Paste the `NEXT_BIND_ENV` lines from the forge log into the **API** environment (Vercel serverless, Fly, Docker, etc.):

- `ERC8004_DEV_CHAIN_ID=11155111`
- `ERC8004_RPC_URL=<same RPC you used>`
- `ERC8004_IDENTITY_REGISTRY_ADDRESS=…`
- `ERC8004_ONCHAIN_AGENT_ID=…`
- `ERC8004_VALIDATION_REGISTRY_ADDRESS=…`
- `ERC8004_REPUTATION_REGISTRY_ADDRESS=…`
- Optional EIP-712: `VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT` = adapter from proof JSON; `VERITRADE_INTENT_SIGNER_PRIVATE_KEY` = **agent** key.
- `VERITRADE_AGENT_WALLET_PLACEHOLDER` = agent address (informational mirror).

Then:

```bash
python scripts/export_agent_registration_static.py
```

Commit or deploy the updated `apps/web/public/.well-known/agent-registration.json` so the **HTTPS** file matches the API.

## Verify

- Browser: `https://YOUR_DOMAIN/.well-known/agent-registration.json` — must show `registrations[]` with your identity address + `agentId`.
- API: `GET https://YOUR_API/challenge/agent-registration` — same `registrations`.
- API: `GET https://YOUR_API/challenge/agent-registration/verify` — check `static_json_matches_api_json`, `api_registrations_match_env`, **`registrations_agent_uri`**, and `transport_observation` for HTTPS URLs.
- On-chain read (optional): `GET …/challenge/erc8004/onchain-read` with `ERC8004_RPC_URL` pointed at Sepolia.

## Reproduce Anvil local proof (unchanged)

Local proof remains **`LocalProofBundle.s.sol`** on Anvil — see [ERC8004_LOCAL_PROOF_WALKTHROUGH.md](ERC8004_LOCAL_PROOF_WALKTHROUGH.md) and [ANVIL_WALLET_ROLES.md](ANVIL_WALLET_ROLES.md).

## If you are blocked

- **No Sepolia ETH:** use a faucet; the repo cannot mint test ETH for you.
- **No HTTPS host:** deploy web first; do not set `PUBLIC_AGENT_REGISTRATION_URL` to a URL you do not control.
- **Script reverts:** ensure `PUBLIC_AGENT_REGISTRATION_URL` is non-empty and keys are valid hex private keys.
