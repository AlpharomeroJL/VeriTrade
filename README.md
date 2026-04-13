# VeriTrade

VeriTrade is a **governed autonomous trading workstation** that ingests **configurable market data** (including **live Kraken** when enabled in `.env`) to drive paper-trading decisions, applies risk checks before action, records intent and execution artifacts, and makes the full decision path visible in a chart-first operator UI.

It is designed to demonstrate:

- **live market ingestion**
- **autonomous paper trading**
- **risk-gated decision making**
- **intent commitment and validation artifacts**
- **operator visibility across spot and futures-style lanes**

## What is live vs simulated

| Surface | Default |
|---------|---------|
| Execution | **Paper / simulated only** — no live orders by default (`ALLOW_REAL_ORDERS=false`, `ENABLE_LIVE_TRADING=false`) |
| Market data | **Configurable** — demo/synthetic or Kraken-backed paths via `.env` |
| Proof trail | **Real** — DB + filesystem artifacts are recorded and surfaced in the UI and API |

## Judge fast path

Start here: **[JUDGES_START_HERE.md](JUDGES_START_HERE.md)**

That file gives the shortest path to:

- running the app
- opening the right mode
- understanding what is live vs simulated
- finding the proof / trust surfaces

## Quick start

**Requirements:** Python 3.11+, Node.js 20+

Use **two terminals** — the API keeps running in the first while the web dev server runs in the second.

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

Ports and URLs come **only** from `.env` (e.g. web **34110**, API **34120** — see `.env.example`).

---

## Challenge alignment (scoring)

| Doc | Why open it |
|-----|-------------|
| [docs/challenge-alignment.md](docs/challenge-alignment.md) | Rubric map: Kraken, trust, artifacts |
| [docs/map-kraken.md](docs/map-kraken.md) | What maps to Kraken (draft, routing, flags) |
| [docs/map-erc8004.md](docs/map-erc8004.md) | Identity / validation / intent binding (draft-aligned language) |
| [docs/erc8004-alignment.md](docs/erc8004-alignment.md) | What is implemented vs scaffolded vs **not** claimed for EIP-8004 |
| [docs/erc8004-compliance-matrix.md](docs/erc8004-compliance-matrix.md) | Requirement × status × **proof** (evidence spine) |
| [docs/erc8004-compliance-checklist.md](docs/erc8004-compliance-checklist.md) | Summary checklist (points to matrix) |
| [docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md](docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md) | Anvil + `LocalProofBundle` + `prove_local_slice` |
| [docs/evidence/PUBLIC_SEPOLIA_DEPLOY.md](docs/evidence/PUBLIC_SEPOLIA_DEPLOY.md) | **Public Sepolia** deploy + mint + HTTPS `/.well-known` binding (operator-funded) |
| [docs/deployment/VERCEL_WEB.md](docs/deployment/VERCEL_WEB.md) | Vercel **web** root (`apps/web`), `VITE_API_BASE_URL`, prebuild `/.well-known` sync |
| [docs/evidence/ANVIL_WALLET_ROLES.md](docs/evidence/ANVIL_WALLET_ROLES.md) | Anvil accounts **0/1/2** roles, RPC, MetaMask/Rabby |
| [`.env.anvil.example`](.env.anvil.example) | Local-only env hints (public Anvil keys) |
| [docs/intent-envelope.md](docs/intent-envelope.md) | SHA-256 intent commitment vs optional EIP-712 signing (dev) |
| [docs/combined-submission.md](docs/combined-submission.md) | One narrative for dual-track reads |

**API:** `GET /overview` (includes `challenge`) · `GET /challenge/context` · `GET /challenge/agent-registration` · `GET /challenge/agent-registration/verify` · `GET /challenge/erc8004/onchain-read` · `GET /challenge/erc8004-shapes`

VeriTrade is **ERC-8004 draft-aligned** (registration file, identity surfaces, validation-shaped examples). **Public Sepolia** deployment is **operator-run** via Foundry (`SepoliaDeployAndMint`, `PUBLIC_SEPOLIA_DEPLOY.md`); it is **not** a protocol-mandated canonical mainnet registry. The product is **not** claiming full EIP compliance — see [docs/erc8004-alignment.md](docs/erc8004-alignment.md).

---

## Where to look in the app

1. **Live Paper Trading** — chart-first desk, autonomous loop, lanes, operator strip.  
2. **Guided Proof Demo** — seed → run cycle → proof trail walkthrough.  
3. **Market Watch** — tape + Kraken session launchers without emphasizing fills.  
4. Expand **Proof & trust** / **More tools** for pipeline, integration tiles, scenarios, raw artifacts.

---

## Tests

```powershell
python -m pytest tests -q
```

**Playwright** (from `apps/web` after `npm install`): `npx playwright install chromium` then `npm run test:e2e`. Soak reports (if you run them) stay under `apps/web/e2e-results/` — **gitignored**.

---

## Repo map

| Path | Role |
|------|------|
| `apps/api/` | FastAPI app, services, Kraken adapters, challenge context |
| `apps/web/` | Vite + React operator console |
| `tests/` | Pytest (integration, risk, intent, lanes, viz) |
| `scripts/` | `dev-api.ps1`, `dev-web.ps1`, `export_agent_registration_static.py` |
| `local-registry/` | Optional Foundry contracts for **Anvil-only** Identity / Validation / Reputation event demos |
| `docs/` | Architecture, trust, challenge maps, lean submission notes |
| `compose.yaml` | Optional Postgres/Redis — **not** required for SQLite demo |

---

## Submission helpers (optional)

| Doc |
|-----|
| [docs/submission/summary.md](docs/submission/summary.md) |
| [docs/submission/submission-description.md](docs/submission/submission-description.md) |
| [docs/submission/demo-flow-finalist.md](docs/submission/demo-flow-finalist.md) |
| [docs/submission/finalist-screenshots.md](docs/submission/finalist-screenshots.md) |
| [docs/submission/screenshot-checklist.md](docs/submission/screenshot-checklist.md) |

Deeper architecture and demo detail: [docs/architecture.md](docs/architecture.md), [docs/demo-script.md](docs/demo-script.md), [docs/trust-and-risk.md](docs/trust-and-risk.md), [docs/known-gaps.md](docs/known-gaps.md).

---

## Docker

[compose.yaml](compose.yaml) — optional services on separate ports; default demo uses **SQLite** without Compose.
