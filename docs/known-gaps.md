# VeriTrade — Known gaps (honest list)

This repository is an **overnight thin slice** for demo credibility. The following are **stubbed, simplified, or missing** by design.

For the **trust story** we *do* claim in-scope, see [trust-and-risk.md](trust-and-risk.md) and [challenge-alignment.md](challenge-alignment.md).

**Kraken:** CLI draft is **real in code**; **live** submission via Kraken is **out of scope** unless you deliberately enable flags. **ERC-8004:** this repo ships a **draft-shaped registration file**, **API alignment fields**, and **validation/reputation example JSON** — **not** deployed Identity / Validation / Reputation registry contracts. Do **not** read “alignment” as “fully compliant.” Details: [erc8004-alignment.md](erc8004-alignment.md).

## Market data

- **Mock snapshots only** — no live WebSocket/REST feed, no multi-venue consolidation.
- **Staleness** is time-based on snapshot timestamp (tunable threshold in code).

## Strategy

- **Single baseline strategy** (`baseline_ma`) — not competitive alpha; demonstrates the **pipeline** only.

## Execution

- **In-process paper simulator** — instant fill at last snapshot mid/price; no order book, slippage model, or partial fills.
- **Kraken / live adapters** are disabled (`ENABLE_KRAKEN_EXECUTION=false`, `ALLOW_REAL_ORDERS=false`).

## Risk

- **Policy** is a small ordered rule set in code + env thresholds — not a full compliance rules engine.
- **Escalate for review** creates an intent in `escalated_for_review` status but has **no human inbox UI**.

## Performance

- **PnL / drawdown** are simplified cash + position notional accounting suitable for the demo, not fund-grade reporting.

## Frontend

- **Polling** only — no SSE/WebSocket live stream.
- **Operator console** styling is functional, not a full design system.

## Infra

- **SQLite** default — Postgres/Redis in `compose.yaml` are optional and **not wired** into the default app path.
- **Worker** port in `.env` is reserved; no separate worker process in this slice.

## Future (if extending)

- Live data adapter behind the same snapshot interface.
- Realistic paper simulator (latency, partial fills).
- Alembic migrations; auth; multi-user tenancy.
- Rich replay (correlation ids across entities).
