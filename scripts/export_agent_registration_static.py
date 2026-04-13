#!/usr/bin/env python3
"""Render `apps/web/public/.well-known/agent-registration.json` from `.env` via the same merge logic as the API.

Run from repository root (requires `apps/api` on `PYTHONPATH`):

    python scripts/export_agent_registration_static.py

This keeps the static Vite-served file aligned with `GET /challenge/agent-registration` after you change
registry binding env vars or base URLs. It does **not** start servers.

**Vercel:** `apps/web` runs `node ./scripts/sync-public-agent-registration.mjs` before `vite build`, using
`VITE_API_BASE_URL` and Vercel system URLs (or overrides). Use this script for local/offline sync from `.env`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    api_dir = root / "apps" / "api"
    sys.path.insert(0, str(api_dir))
    os.chdir(api_dir)

    from dotenv import load_dotenv

    load_dotenv(root / ".env")
    load_dotenv(root / ".env.example", override=False)

    from app.challenge.registration import build_agent_registration
    from app.config import get_settings

    get_settings.cache_clear()
    doc = build_agent_registration(get_settings())
    out = root / "apps" / "web" / "public" / ".well-known" / "agent-registration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
