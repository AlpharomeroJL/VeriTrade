# VeriTrade

VeriTrade is a **local demo workstation**: a **FastAPI** backend (SQLAlchemy, default **SQLite**) plus a **Vite + React** operator UI. It walks a single pipeline—**market snapshot → signal → risk → trade intent → simulated execution**—with rows and JSON **artifacts** persisted for inspection. Optional paths add **read-only Kraken public data**, **CLI-shaped order drafts** (never submitted by this repo), **two “lane” heuristics** (spot vs futures-style labels on the same paper simulator), and **ERC-8004–shaped** registration JSON plus optional JSON-RPC **read** helpers.

This README describes **what the code does**. Other Markdown under `docs/` may be older or contest-oriented; trust the implementation and tests when they disagree.

---

## Execution (read this first)

**There is no implemented path that sends orders to Kraken or any exchange.**

Fills always go through `execution_service.simulate_execution`, which calls `assert_paper_only()`. That function **raises** unless all of the following are true:

- `ALLOW_REAL_ORDERS` is false  
- `ENABLE_LIVE_TRADING` is false  
- `EXECUTION_PROVIDER` is exactly `paper` (case-insensitive)

So `ENABLE_KRAKEN_EXECUTION` and `ALLOW_REAL_ORDERS` only affect **UI/API narrative** (e.g. `kraken_surface.routing_mode`, safety strip `live_trading_enabled` when **both** flags are true). They do **not** switch the executor.

**Kraken in this repo means:** HTTPS **public** ticker/OHLC (no API keys in code paths), optional **CLI** ticker via your shell template, and a **typed JSON draft** (`build_kraken_cli_order_draft`) describing what a CLI layer *could* consume—not live routing.

---

## What is “live” vs simulated

| Surface | Behavior in code |
|--------|-------------------|
| **Order execution** | Always **in-process paper** fills/rejects as above. No venue order I/O. |
| **Market tape** | **`MARKET_DATA_MODE`:** `demo` (random mock snapshots), `kraken_public` (Kraken REST ticker for BTC/ETH/SOL USD pairs), or `kraken_cli` (subprocess + `KRAKEN_MARKET_CLI_TICKER_TEMPLATE`). CLI failures fall back to mock with explicit `source` on snapshots. |
| **“Volatility” flag on Kraken snapshots** | **Computed locally** from bid/ask spread vs mid (not Kraken’s own vol index). |
| **OHLC / charts** | May use Kraken public OHLC when tape mode is `kraken_public` or `kraken_cli`, with **per-symbol throttling** (~55s) to limit public API calls; otherwise bars are built from stored snapshots. |
| **Artifacts + DB** | **Real persistence**: `artifacts` table and JSON files under `ARTIFACTS_DIR`. |
| **Trust / “fit” scores in API** | **Heuristic counters** derived from DB rows (`rubric_service`), not chain proofs or ML. |

---

## Operator UI (web)

One SPA with three **modes** (labels in `apps/web/src/dashboard/modeCopy.ts`):

1. **Guided Proof Demo** — stepwise use of seed / run / proof copy.  
2. **Live Paper Trading** — chart, `/overview`, autonomous loop, lanes, scenarios.  
3. **Market Watch** — same API; emphasizes tape/context. **Tape** is still whatever `MARKET_DATA_MODE` selects; there is no separate “watch-only” backend.

The web client uses **`VITE_API_BASE_URL`** for all fetches (`apps/web/src/api.ts`).

---

## Quick start

**Requirements:** Python 3.11+, Node.js 20+

Use **two terminals** — API in the first, web in the second.

**Terminal 1 — API**

```powershell
copy .env.example .env
python -m pip install -e "apps/api[dev]"
python -m uvicorn app.main:app --app-dir apps\api --host 0.0.0.0 --port $env:VERITRADE_API_PORT --reload
```

**Terminal 2 — web**

```powershell
cd apps\web
npm install
npm run dev
```

Ports and origins must match what the API’s **`Settings`** expects: at minimum `VERITRADE_API_PORT`, `VERITRADE_API_BASE_URL`, `VERITRADE_WEB_BASE_URL`, `VERITRADE_WEB_PORT`, and `DATABASE_URL` (see `apps/api/app/config.py`). Defaults in `.env.example` use **34110** (web) and **34120** (API).

---

## Architecture (code-level)

| Piece | Role |
|--------|------|
| **`pipeline_service`** | Core loop: ingest → candles → signal → risk → intent (if not blocked/skipped/review) → **paper** execution → artifacts → performance on fill. |
| **`strategy_service`** | MA-style signals from 1m closes when enough candles exist; cold-start uses fewer snapshots or randomness. |
| **`risk_engine`** | Verdicts: `allow`, `allow_with_reduction`, `block`, `escalate_for_review`, `skip`. Blocks stale snapshots **> 120s**. Duplicate guard on recent **filled** same-direction trades (default 30 min core, 2 min lanes). **`no_trade` on `SystemControl` is not toggled by any public route**—only reset in demo flows. |
| **`lane_service`** | Two seeded lanes (`spot_momentum`, `futures_tactical`) with separate heuristics and caps; artifacts `lane_signal`, `lane_risk`, `lane_execution`. **`run_lane_once` passes `manual_pause=False` and `no_trade=False`**—global pause/no-trade do not apply to lane runs as written. |
| **`autonomous_service`** | Background thread: if **any** lane is `running`, runs **`run_lane_once` for the first such lane** (by `lane_id` order); else runs the core pipeline. Cadence **5–120s**. Starting autonomous sets system control to **`running`**. |
| **`kraken_skills_service`** | Separate **session** CRUD: CLI verify, briefs, watch snapshots, toy paper sessions (fixed uplift math), etc. **Not** wired into `trade_intents` / core pipeline. |
| **`challenge/*` + `/challenge/*` routes** | Registration JSON merge, verify report, optional `web3` **view** calls, EIP-712 digest/recover/ERC-1271 helpers, static example payloads from `spec-alignment/schemas/`. |
| **`registration.py`** | Builds agent registration from **`spec-alignment/agent-registration.json`** plus `.env` URLs and optional on-chain `registrations` / `agentWallet` fields. |

**Overview payload:** `GET /overview` ties “latest” signal/intent/execution to the **latest risk decision** when one exists; otherwise it falls back to latest rows per table (`routes.overview`).

**Stale check:** `pipeline_service` calls `snapshot_is_stale` but **does not act** on it (no auto-refresh); risk still enforces the 120s rule.

---

## HTTP API (surface)

Implemented under `apps/api/app/api/routes.py` (prefix `/` on router):

- **Health:** `GET /health`, `GET /ready`  
- **Operator:** `GET /overview`, `GET /performance`, `GET /activity`, `GET /signals`, `GET /risk-decisions`, `GET /intents`, `GET /executions`, `GET /artifacts`, `GET /alerts`  
- **Viz:** `GET /viz/market-chart` (intervals `1m`, `5m`, `15m`, `30m`, `1h`), `GET /viz/paper-session`  
- **Control:** `POST /control/start|pause|stop`, `POST /control/manual-pause`, `POST /control/step`, `POST /control/autonomous/start|stop`  
- **Demo:** `POST /demo/seed`, `POST /demo/run-once`, `POST /demo/scenario/{safe_allow\|volatile_block\|oversized_reduce}`  
- **Lanes:** `GET /lanes`, `GET /lanes/{id}`, `GET /lanes/{id}/performance`, `GET /lanes/{id}/history`, `POST /lanes/{id}/start|stop|run-once`  
- **Kraken skills:** `POST /kraken-skills/run`, `GET /kraken-skills/sessions`, `GET /kraken-skills/sessions/{id}`  
- **Challenge / ERC-8004-shaped:** `GET /challenge/context`, `GET /challenge/agent-registration`, `GET /challenge/agent-registration/verify`, `GET /challenge/erc8004-shapes`, `GET /challenge/erc8004/onchain-read`  
- **Intents:** `GET /intents/{id}/signature-verification` (EIP-712 digest, optional recovery, optional ERC-1271 `eth_call`)

Schemas live in `apps/api/app/schemas/api.py`.

---

## Configuration

**Source of truth for the API:** `apps/api/app/config.py` (`pydantic-settings`, `extra="ignore"`).

`.env.example` lists many variables; **only those mapped in `Settings` affect Python**. For example, flags like `ENABLE_DEMO_SEED`, `ENABLE_REPLAY_VIEW`, `DATABASE_PROVIDER`, Redis/Postgres URLs, `KRAKEN_API_KEY`, etc. are **not read** by `Settings` and **do not change** FastAPI behavior unless you add code or external tooling.

Important execution and market keys that **are** read: `TRADING_MODE`, `EXECUTION_PROVIDER`, `ENABLE_LIVE_TRADING`, `ALLOW_REAL_ORDERS`, `ENABLE_KRAKEN_EXECUTION`, `MARKET_DATA_MODE`, `KRAKEN_MARKET_CLI_*`, `KRAKEN_CLI_*`, `ARTIFACTS_DIR`, `DATABASE_URL`, ERC-8004 / EIP-712 fields as defined on `Settings`.

**Misconfiguration note:** if `EXECUTION_PROVIDER` is not `paper`, the app will **throw** when it tries to execute—there is no alternate executor implemented.

---

## Agent registration file (static web)

- **Runtime JSON:** `GET /challenge/agent-registration` (merged template + env).  
- **Committed static copy:** `apps/web/public/.well-known/agent-registration.json` (localhost template).  
- **Prebuild:** `apps/web/scripts/sync-public-agent-registration.mjs` runs before `vite build`. On **Vercel**, the build **fails** if public web + API bases cannot be resolved. Locally it **skips** unless `VERITRADE_PUBLIC_WEB_BASE_URL` **and** `VITE_API_BASE_URL` (or `VERITRADE_PUBLIC_API_BASE_URL`) are set.

Template: `spec-alignment/agent-registration.json`.

---

## Optional on-chain demos

- **`local-registry/`** — Foundry contracts (Anvil / testnet demos): identity, validation, reputation helpers; **not** audited production registries.  
- **Artifact → `validationRequest` tx** — **off by default** (`ERC8004_ARTIFACT_VALIDATION_EMIT_ENABLED`); requires RPC, key, registry, validator, numeric agent id; failures do not block artifact writes.

---

## Tests

```powershell
python -m pytest tests -q
```

**Playwright** (from `apps/web` after `npm install`): `npx playwright install chromium` then `npm run test:e2e`. Reports under `apps/web/e2e-results/` are **gitignored**.

---

## Repo map

| Path | Role |
|------|------|
| `apps/api/` | FastAPI app (`app/main.py`, `app/api/routes.py`, services, adapters, `challenge/`) |
| `apps/web/` | Vite + React UI, Playwright e2e, `public/.well-known/` |
| `tests/` | Pytest |
| `scripts/` | Helpers (e.g. `export_agent_registration_static.py`, `scripts/erc8004/*`) |
| `spec-alignment/` | Registration template + example JSON schemas |
| `local-registry/` | Solidity + Foundry scripts for local/testnet demos |
| `docs/` | Extra notes, deployment, evidence (may lag code) |
| `compose.yaml` | **Only** Postgres 16 and Redis 7 — **no app container**; API still defaults to SQLite without Compose |

---

## Docker

`compose.yaml` starts **database and cache only** on the mapped ports. The default dev flow does **not** require Docker; point `DATABASE_URL` at Postgres only if you wire that yourself (the example app code is built around SQLAlchemy generically, but day-to-day demo is SQLite).

---

## Further reading (may not match every detail of `main`)

- [START_HERE.md](START_HERE.md) — short navigation.  
- [JUDGES_START_HERE.md](JUDGES_START_HERE.md) — quick demo path (verify against this README if something looks off).  
- `docs/` — challenge alignment, deployment (e.g. Vercel), ERC-8004 narrative; **treat as supplementary**.

When in doubt, read **`apps/api/app/config.py`**, **`apps/api/app/api/routes.py`**, and **`apps/api/app/services/`**.
