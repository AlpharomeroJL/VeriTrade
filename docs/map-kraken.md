# What maps to Kraken

## Product story

VeriTrade separates **(A) governance + intent + risk** from **(B) venue routing**. The demo **always** exercises (A). Path **(B)** is real in architecture: a **Kraken execution surface** that can emit **CLI-shaped order drafts** aligned with how you would wire the official tooling — without turning on live orders for the hackathon video.

## Concrete mappings

| Kraken challenge idea | VeriTrade implementation |
|-----------------------|---------------------------|
| **CLI / API execution path** | `KrakenExecutionSurface`: `build_kraken_cli_order_draft()` returns JSON (`pair`, `side`, `volume`, `ordertype`, `intent_uuid`, …). |
| **Safety / paper** | Active fills use **paper simulator** in `execution_service`. `routing_mode` in API explains `paper_simulator` vs `kraken_cli_surface_ready` vs gated live. |
| **Intent → order** | Draft is built from the **canonical trade intent** + latest **mark price** (same inputs as paper fill). |
| **Observability** | Operator UI shows **Execution (venue path)** + **Kraken surface** note in **Agent identity** panel. |

## Environment

| Variable | Role |
|----------|------|
| `KRAKEN_CLI_SURFACE_ENABLED` | When `true` (default), API reports `kraken_cli_surface_ready` routing for narrative. |
| `KRAKEN_CLI_COMMAND_STUB` | Display / draft field for the CLI binary name (default `kraken`). |
| `ENABLE_KRAKEN_EXECUTION` | Must pair with `ALLOW_REAL_ORDERS` for any future live routing (off in submission). |

## Files

- [`apps/api/app/adapters/kraken_execution_surface.py`](../apps/api/app/adapters/kraken_execution_surface.py)
- [`apps/api/app/services/execution_service.py`](../apps/api/app/services/execution_service.py) — paper fills
- [`apps/api/app/challenge/context.py`](../apps/api/app/challenge/context.py) — bundles Kraken surface into `GET /overview`
