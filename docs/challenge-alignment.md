# Challenge alignment (VeriTrade)

VeriTrade is framed as a **combined submission**: **Kraken-aware execution surface** + **governed agent behavior** that mirrors **ERC-8004-style** trust primitives (identity, validation, discoverability) **without** pretending full on-chain deployment in this repo.

## Rubric mapping (single table)

| Challenge theme | What VeriTrade shows | Where |
|-----------------|----------------------|--------|
| **Kraken / venue execution path** | Typed **Kraken CLI order draft** + `routing_mode`; live path **gated** behind env flags. Default fills: **paper simulator**. | `GET /overview` → `challenge.kraken_surface`, [`apps/api/app/adapters/kraken_execution_surface.py`](../apps/api/app/adapters/kraken_execution_surface.py) |
| **Agent identity** | Stable **`VERITRADE_AGENT_ID`** surfaced to UI + API. | `GET /overview` → `challenge.agent_id` |
| **Signed / binding trade intents** | **`intent_commitment_sha256`** — deterministic SHA-256 over canonical intent fields (off-chain commitment for demo). | `GET /overview` → `latest_intent.intent_commitment_sha256` |
| **Validation artifacts** | Persisted **artifact** rows + JSON files (`signal`, `risk`, `intent`, `execution`). | Dashboard **Validation artifact trace**, `GET /activity` |
| **Trust signals** | Enumerated list in API for judges (`trust_signals`). | `GET /overview` → `challenge.trust_signals` |
| **Risk-router enforcement** | Ordered policy → **allow / allow_with_reduction / block / escalate_for_review** before execution. | **Risk router** card, `risk_decisions` |
| **Operator control** | Pause / step / stop / manual risk pause. | Operator controls |

Deep dives:

- [map-kraken.md](map-kraken.md)
- [map-erc8004.md](map-erc8004.md)
- [combined-submission.md](combined-submission.md)

## What we explicitly do *not* claim

- **No default live Kraken trading** — `ALLOW_REAL_ORDERS=false`, `TRADING_MODE=paper` for submission safety.
- **No full ERC-8004 registry on-chain** in this slice — optional `ERC8004_AGENT_URI_STUB` for narrative and future wiring.

## API

- `GET /overview` — includes full **`challenge`** object (identity, trust signals, Kraken surface, draft order when intent + snapshot exist).
- `GET /challenge/context` — same `challenge` payload alone (easy for judges / scripts).
