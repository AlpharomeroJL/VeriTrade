# Paste-ready submission description (finalist)

**Title:** VeriTrade — Governed autonomous trading with Kraken surface + trust-native artifacts

**Short description (≈280 characters):**  
VeriTrade is a production-minded operator console for risk-governed AI trading: every cycle flows strategy signal → risk router → signed intent (SHA-256 commitment) → venue execution, with a persisted validation artifact chain. Paper execution proves the loop safely; a typed Kraken CLI order draft shows explicit venue alignment. Built for combined “Kraken + trustless agent” judging — no live orders required.

**Long description (submission box):**  
VeriTrade demonstrates how autonomous trading agents should behave in serious environments: nothing executes without an explicit risk-router verdict, a canonical signed trade intent, and durable validation artifacts (database + JSON). The operator UI is designed like premium internal SaaS: clear hierarchy, evidence chain, and challenge-native framing for Kraken and ERC-8004-style trust themes.

The default demo runs entirely in paper mode so judges can verify governance without capital risk. In parallel, the system exposes a Kraken execution surface that materializes structured CLI order drafts from the same signed intent, making venue wiring obvious without forcing live trading during review. Agent identity, enumerated trust signals, and optional registry URI stubs document how the same architecture attaches to trustless-agent registries later.

Stack: FastAPI, SQLite, Vite/React. Documentation maps every rubric claim to API routes and UI surfaces. Tests cover risk behavior and an end-to-end demo loop.

**Repo highlights:** `docs/challenge-alignment.md`, `GET /overview` (includes `challenge`), `GET /challenge/context`.

**What we did not chase tonight:** live Kraken execution, on-chain deployment, auth, multi-tenant infra.
