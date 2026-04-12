# What maps to ERC-8004 (trustless agent) themes

ERC-8004 (and adjacent “trustless agent” framing) emphasizes **discoverable identity**, **validation**, and **auditable behavior**. VeriTrade aligns **conceptually** and with **off-chain stubs** so judges see where on-chain registration would attach — without shipping a registry contract in this repo.

## Mappings

| ERC-8004-style theme | VeriTrade slice |
|----------------------|-----------------|
| **Agent identity** | `VERITRADE_AGENT_ID` in config + UI. Optional `ERC8004_AGENT_URI_STUB` (metadata URI / registry link placeholder). |
| **Validation / reputation signals** | **Trust signals** list in API; **validation artifacts** (DB + filesystem); **risk router** verdicts as machine-readable policy outcomes. |
| **Transparency** | **Validation artifact trace** (chronological); **intent commitment** hash binds intent fields pre-execution. |
| **Interoperability hook** | `GET /challenge/context` — stable JSON for external tools / future registry. |

## Non-claims

- No on-chain **AgentRegistration** or **Validation** contract in this repository.
- **Intent commitment** is **SHA-256 over canonical JSON** (off-chain). Swapping to EIP-712 or registry attestation is a documented upgrade path in [known-gaps.md](known-gaps.md).

## Env

| Variable | Purpose |
|----------|---------|
| `VERITRADE_AGENT_ID` | Stable agent id string for demos and docs. |
| `ERC8004_AGENT_URI_STUB` | Optional URI string (e.g. future IPFS or registry URL) — empty is fine. |
