# Vercel — web app (static `/.well-known` + SPA)

The operator-facing registration file lives at:

`apps/web/public/.well-known/agent-registration.json`

Vite copies `public/` into `dist/` unchanged, so production URL shape is:

`https://<project>.vercel.app/.well-known/agent-registration.json`

## Project settings

| Setting | Value |
|--------|--------|
| **Root Directory** | `apps/web` |
| **Framework Preset** | Vite (or Other + `npm run build`) |
| **Build Command** | `npm run build` (runs `prebuild` first — see below) |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

`vercel.json` in `apps/web` adds an SPA fallback rewrite. **Static files under `public/` are still served** before the SPA rewrite (Vercel + Vite default behaviour).

## Environment variables (Vercel project)

| Variable | Required | Purpose |
|----------|----------|---------|
| **`VITE_API_BASE_URL`** | **Yes** on Vercel | Public HTTPS origin of the FastAPI app (no trailing slash), baked into the SPA and into the prebuilt `/.well-known` registration JSON. |
| **`VERITRADE_PUBLIC_WEB_BASE_URL`** | No | Override the public web origin in `agent-registration.json` if it must differ from Vercel’s production or preview hostname. |
| **`VERITRADE_PUBLIC_API_BASE_URL`** | No | Fallback API base if you cannot reuse `VITE_API_BASE_URL` for the registration merge (same shape: `https://api.example.com`). |
| **`ERC8004_*` / `VERITRADE_AGENT_WALLET_PLACEHOLDER` / `ERC8004_AGENT_URI_STUB`** | No | Same semantics as the API: when set on the Vercel build, the prebuild can emit `registrations[]` / `agentWallet` into the static JSON (optional). |

**System variables:** Leave **Expose System Environment Variables** enabled so `VERCEL_PROJECT_PRODUCTION_URL` / `VERCEL_URL` are available during build (used for the default public web origin in the registration file).

Set `VITE_API_BASE_URL` in the Vercel dashboard (**Settings → Environment Variables**) for **Production** (and **Preview** if you use previews). Do not invent a value: use the real public URL of your deployed API.

## Option B — API is canonical; static file stays aligned

Runtime source of truth for registration JSON is **`GET /challenge/agent-registration`** on the API (`apps/api/app/challenge/registration.py`), using **`VERITRADE_WEB_BASE_URL`** and **`VERITRADE_API_BASE_URL`** on the API host.

On each Vercel web build, **`npm run prebuild`** runs `apps/web/scripts/sync-public-agent-registration.mjs`, which applies the **same merge** to `spec-alignment/agent-registration.json` and overwrites `apps/web/public/.well-known/agent-registration.json` before `vite build`. That keeps the hosted `/.well-known` file consistent with the API when env vars match.

For **local** sync from `.env` (without Vercel), use:

```bash
python scripts/export_agent_registration_static.py
```

## Rename the Vercel project (optional)

The CLI may not expose rename; in the dashboard open **Project → Settings → General → Project Name** and set something like **`veritrade`**. `.vercel/project.json` is gitignored; after a rename, run `vercel link` from `apps/web` if you need to refresh the local link.
