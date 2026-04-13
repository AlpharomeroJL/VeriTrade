# ERC-8004 draft alignment (scaffolding)

This folder holds **truthful, draft-shaped** artifacts for [ERC-8004: Trustless Agents (DRAFT)](https://eips.ethereum.org/EIPS/eip-8004). Nothing here claims **live on-chain deployment** unless you wire it yourself.

| Path | Purpose |
|------|---------|
| [`agent-registration.json`](agent-registration.json) | Registration file matching EIP § *Agent URI and Agent Registration File* (defaults match `.env.example` localhost URLs). |
| [`contracts/`](contracts/) | **Illustrative** Solidity interfaces mirroring registry responsibilities — not deployed, not audited. |
| [`schemas/`](schemas/) | Example **off-chain** JSON shapes for validation requests/responses and reputation-style feedback. |

**Dynamic registration** (endpoints taken from your `.env`): `GET {VERITRADE_API_BASE_URL}/challenge/agent-registration`

**Static copy** (for `.well-known` on the web origin): `apps/web/public/.well-known/agent-registration.json` — should stay in sync with `agent-registration.json` defaults; prefer the API route when ports differ from examples.
