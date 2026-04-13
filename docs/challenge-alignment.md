# Challenge alignment (VeriTrade)

VeriTrade is framed as a **combined submission**: **Kraken-aware execution surface** + **governed agent behavior** that is **ERC-8004 draft-aligned** on identity, registration file shape, and validation-*shaped* artifacts **without** claiming full protocol compliance or live registry deployment in this repo.

**Alignment details:** [erc8004-alignment.md](erc8004-alignment.md)

## Rubric mapping (single table)

| Challenge theme | What VeriTrade shows | Where |
|-----------------|----------------------|--------|
| **Kraken / venue execution path** | Typed **Kraken CLI order draft** + `routing_mode`; live path **gated** behind env flags. Default fills: **paper simulator**. | `GET /overview` → `challenge.kraken_surface`, [`apps/api/app/adapters/kraken_execution_surface.py`](../apps/api/app/adapters/kraken_execution_surface.py) |
| **Agent identity** | Stable **`VERITRADE_AGENT_ID`** + **`challenge.erc8004_draft`** (registration URLs, registry status). | `GET /overview` → `challenge` |
| **EIP registration file** | **`GET /challenge/agent-registration`** + **`/.well-known/agent-registration.json`** (draft `type`, honest `services`, empty `registrations` until mint). | API + static web |
| **Signed / binding trade intents** | **`intent_commitment_sha256`** — SHA-256 over canonical intent fields (off-chain). EIP-712 outline: [intent-envelope.md](intent-envelope.md). | `GET /overview` → `latest_intent.intent_commitment_sha256` |
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
- **No “ERC-8004 compliant” or live registry-backed identity** in this slice — optional `ERC8004_AGENT_URI_STUB` and **`registrations: []`** until you mint on a real Identity Registry. See [erc8004-alignment.md](erc8004-alignment.md).

## API

- `GET /overview` — includes full **`challenge`** object (identity, trust signals, Kraken surface, draft order when intent + snapshot exist).
- `GET /challenge/context` — same `challenge` payload alone (easy for judges / scripts).
- `GET /challenge/agent-registration` — EIP-8004-shaped registration JSON (endpoints from `.env`).
- `GET /challenge/erc8004-shapes` — example validation / off-chain reputation JSON (documentation).
