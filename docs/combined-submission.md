# Combined submission narrative

VeriTrade is intentionally a **single story** that satisfies **two judge lenses** at once:

1. **Kraken challenge** — “Real venue path exists in the architecture; the demo runs safely on **paper** while showing **CLI-shaped** order drafts.”
2. **Trustless / ERC-8004 draft-aligned agent challenge** — “The agent has **identity surfaces**, **policy**, **binding intents**, **validation artifacts**, and an **EIP-shaped registration file** — a credible path to registry-backed trust without claiming live on-chain compliance in this repo.”

## One paragraph (paste into submission form)

> VeriTrade is a governed trading agent that **never executes without a risk-router verdict** and a **canonical trade intent** (SHA-256 commitment over binding fields). Every stage emits **validation artifacts** (database + JSON). **Paper mode** runs the full loop for judges; a **Kraken execution surface** produces **typed CLI order drafts** from the same intent so venue wiring is explicit. **ERC-8004 draft alignment** includes a real **registration JSON** (`/.well-known/agent-registration.json` + API), **`challenge.erc8004_draft`** metadata, and **validation-shaped** examples — **not** a claim of live Identity / Validation / Reputation registry deployment.

## Demo order (2–3 minutes)

1. Show **Agent identity / trust** (badges + `challenge` fields).  
2. **Seed** → **Run cycle** → **Decision pipeline** + **Validation artifact trace**.  
3. Point at **intent commitment** hash and **Kraken order draft** in overview JSON (or UI copy).  
4. **Pause / Step** — operator bounded autonomy.  

Script: [demo-script.md](demo-script.md) · Checklist: [submission/screenshot-checklist.md](submission/screenshot-checklist.md).

## Evidence artifacts for reviewers

| Artifact | Location |
|----------|----------|
| Challenge alignment | [challenge-alignment.md](challenge-alignment.md) |
| Kraken mapping | [map-kraken.md](map-kraken.md) |
| ERC-8004 mapping | [map-erc8004.md](map-erc8004.md) |
| Architecture | [architecture.md](architecture.md) |
| API | `GET /overview`, `GET /challenge/context` |
