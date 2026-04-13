# Judges — start here

Five-minute path to a fair read of VeriTrade.

## 1. Install and run

```powershell
copy .env.example .env
python -m pip install -e "apps/api[dev]"
python -m uvicorn app.main:app --app-dir apps\api --host 127.0.0.1 --port $env:VERITRADE_API_PORT --reload
```

New terminal:

```powershell
cd apps\web
npm install
npm run dev
```

Open the **web URL** from `.env` (default in `.env.example` is often `http://127.0.0.1:34110`).

## 2. Open **Live Paper Trading**

In the app header, click **Live Paper Trading**.

**What you should see first**

- A **status rail** (tape source, paper execution, autonomous state, lane/loop, timestamps).
- A **large chart** (OHLC + decision markers) and a **right-hand column**: current story, market → bot → risk → execution, and “what changed”.
- An **operator strip**: equity, P/L, drawdown, mode, risk, execution, **autonomous** controls, **Run cycle** / seed / risk pause / stop.

## 3. What is **simulated** vs **live**

| | |
|--|--|
| **Simulated** | Order **fills** and portfolio moves are **paper only**. Default flags block real orders. |
| **Can be live (config)** | **Public market data** may come from **Kraken-backed** paths when enabled in `.env` — still **no** automatic real-money execution in this submission default. |

Check badges in the shell and the hero rail; read `ALLOW_REAL_ORDERS` / `ENABLE_LIVE_TRADING` / `MARKET_DATA_MODE` in `.env.example`.

## 4. Proof and validation

- In **Live Paper**, scroll to **Proof & trust** (collapsed section) — open for **proof trail**, **pipeline**, **integration** (identity / Kraken surface / fit checklist), and **structured artifact** cards.  
- **API:** `GET /overview` includes `challenge` (with **`erc8004_draft`** — draft-aligned, not “fully compliant”) and safety strip fields aligned to the UI.
- **ERC-8004 (draft-aligned + local + public testnet path):** open **`GET {API}/challenge/agent-registration`** for the EIP-shaped registration JSON; **`GET /challenge/agent-registration/verify`** for same-host / fetch checks, **`registrations_agent_uri`** (on-chain `agentURI` document fetch), and optional **`transport_observation`** on `https://` URLs (not CA “HTTPS verified”); **`GET /challenge/erc8004/onchain-read`** for optional JSON-RPC reads (`getValidationStatus`, identity incl. **`agentWallet`**, `getMetadata`, **`feedbackCount`**, **`getFeedback`**); **`GET /intents/{id}/signature-verification`** for EIP-712 digest + recovery + optional ERC-1271 `eth_call` (primary verifying contract + optional **`VERITRADE_EIP1271_SECONDARY_VERIFIER`**); **`GET /challenge/erc8004-shapes`** for validation/reputation *example* payloads. **Evidence spine:** [docs/erc8004-compliance-matrix.md](docs/erc8004-compliance-matrix.md). **Anvil:** [docs/evidence/ANVIL_WALLET_ROLES.md](docs/evidence/ANVIL_WALLET_ROLES.md), `prove_local_slice`, [ERC8004_LOCAL_PROOF_WALKTHROUGH.md](docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md), `LocalProofBundle.s.sol`. **Public Sepolia (operator):** [docs/evidence/PUBLIC_SEPOLIA_DEPLOY.md](docs/evidence/PUBLIC_SEPOLIA_DEPLOY.md), `SepoliaDeployAndMint.s.sol`, [VERCEL_WEB.md](docs/deployment/VERCEL_WEB.md). Read [docs/erc8004-alignment.md](docs/erc8004-alignment.md) for what is real vs simulated vs scaffolded.

## 5. Optional checks

- **Guided Proof Demo** — stepwise seed + run + trail.  
- **Tests:** from repo root, `python -m pytest tests -q`.

For rubric language and mappings: [docs/challenge-alignment.md](docs/challenge-alignment.md).
