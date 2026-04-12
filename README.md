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
| [docs/map-erc8004.md](docs/map-erc8004.md) | Identity / validation / intent binding |
| [docs/combined-submission.md](docs/combined-submission.md) | One narrative for dual-track reads |

**API:** `GET /overview` (includes `challenge`) · `GET /challenge/context`

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
| `scripts/` | `dev-api.ps1`, `dev-web.ps1` |
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
