# Judges — start here

Short path to run VeriTrade and see what the **code** actually does. Details: [README.md](README.md).

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

Open the **web URL** from `.env` (`VERITRADE_WEB_BASE_URL`; `.env.example` often uses `http://127.0.0.1:34110`). Set **`VITE_API_BASE_URL`** in `apps/web/.env` or your environment to the same origin you use for `VERITRADE_API_BASE_URL` (e.g. `http://127.0.0.1:34120`) so the SPA can reach the API.

## 2. Open **Live Paper Trading**

In the app header, choose **Live Paper Trading** (chart-first desk).

**What you should see first**

- A **status rail**: tape source (`MARKET_DATA_MODE`), execution line (`TRADING_MODE` / `EXECUTION_PROVIDER`), autonomous on/off, lane scope, refresh/tape times.
- A **chart** (OHLC + markers from recent intents/executions) and a **decision column**: story, market → bot → risk → execution.
- **Controls**: start / pause / stop, manual risk pause, **Run cycle**, demo **seed**, autonomous start/stop, lane run/start/stop when exposed in this mode.

## 3. What is **simulated** vs **live**

| | |
|--|--|
| **Always simulated (this repo)** | **Order fills** — only `execution_service.simulate_execution` runs. There is **no** code path that submits orders to Kraken or any venue. `ENABLE_KRAKEN_EXECUTION` + `ALLOW_REAL_ORDERS` only change **labels** in the API (`kraken_surface`, safety strip); they do **not** switch the executor. **`EXECUTION_PROVIDER` must stay `paper`** or execution raises. |
| **Can be “live” tape (config)** | **Prices**: `MARKET_DATA_MODE=kraken_public` uses Kraken **public** HTTPS ticker (and optional OHLC) for BTC/ETH/SOL USD-style symbols. `kraken_cli` uses your `KRAKEN_MARKET_CLI_TICKER_TEMPLATE` subprocess; on failure the API falls back to mock snapshots with an explicit `source`. **No API keys are required** for the HTTPS ticker path in code. |
| **Persisted “proof”** | **SQLite** rows and **`ARTIFACTS_DIR`** JSON files — real for the session, not blockchain truth unless you separately deploy contracts and set env vars. |

Check the hero rail and `GET /overview` → `safety_strip` and `challenge.kraken_surface`.

## 4. Proof, trust, and ERC-8004-shaped surfaces

- In **Live Paper**, expand **Proof & trust** for artifact trail, pipeline copy, and integration tiles driven from **`GET /overview`** (`challenge`, `rubric_metrics`, `challenge_fit`, `safety_strip`, `lane_trust`). **`challenge_fit` includes booleans that are partly hardcoded in code** (e.g. `combined_submission_story`, `erc8004_agent_registration_available`); **`trust_score_*` values are heuristics** from DB counts, not audits.
- **`GET /challenge/agent-registration`** — registration JSON merged from `spec-alignment/agent-registration.json` + your `.env` URLs; `registrations` is non-empty only when **both** `ERC8004_IDENTITY_REGISTRY_ADDRESS` and `ERC8004_ONCHAIN_AGENT_ID` are set.
- **`GET /challenge/agent-registration/verify`** — fetches static `/.well-known/agent-registration.json` vs API JSON, host comparisons, optional TLS **observation** (not CA proof), optional fetch of `agentURI` from the first registration entry.
- **`GET /challenge/erc8004/onchain-read`** — optional JSON-RPC **read** calls when `ERC8004_RPC_URL` and registry addresses are set (`web3`). Skips with explicit reasons when not configured.
- **`GET /challenge/erc8004-shapes`** — static **example** JSON from `spec-alignment/schemas/`.
- **`GET /intents/{id}/signature-verification`** — SHA-256 commitment, EIP-712 digest/recover when signature present, optional ERC-1271 `eth_call` when RPC + verifying contract env vars are set (optional secondary verifier).

On-chain demos, Anvil scripts, Sepolia deploy notes, and matrices live under **`docs/`** and **`local-registry/`** — useful for procedure, but **[README.md](README.md) is the accuracy anchor** for runtime behavior.

## 5. Optional checks

- **Guided Proof Demo** — same API; stepwise seed/run UI.
- **Tests:** from repo root, `python -m pytest tests -q`.

Rubric-oriented wording: `docs/challenge-alignment.md` (may not match every line of code).
