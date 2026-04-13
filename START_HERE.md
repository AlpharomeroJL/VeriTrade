# VeriTrade — start here

**New to the repo?** Read [README.md](README.md) first. It matches the implementation: paper-only execution, what `.env` keys actually do, API surface, and known gaps (e.g. lane runs ignore global `manual_pause` / `no_trade` in code).

**Demoing in a hurry?** Use [JUDGES_START_HERE.md](JUDGES_START_HERE.md) — install, open **Live Paper Trading**, and what to look at in the UI and API.

**Extra narrative (may lag the code):** `docs/challenge-alignment.md`, `docs/combined-submission.md`, and other files under `docs/`. If something disagrees with [README.md](README.md) or the tests, trust README + code.

---

## Operator rules

- Ports and API/web origins come from `**.env`** as loaded by `apps/api/app/config.py` (`Settings`).
- **Fills are always the in-process paper simulator** unless you change code: `execution_service.assert_paper_only()` requires `EXECUTION_PROVIDER=paper` and both `ALLOW_REAL_ORDERS` and `ENABLE_LIVE_TRADING` false, or execution **raises**.
- **Kraken in-repo** is read-only market data (HTTPS public API and/or CLI ticker) plus **non-submitting** CLI order **drafts** in JSON — not live exchange orders.
- End-to-end slice: snapshot → signal → risk → intent (when allowed) → paper execution → artifacts → dashboard.

Optional contributor notes: [docs/internal/](docs/internal/).