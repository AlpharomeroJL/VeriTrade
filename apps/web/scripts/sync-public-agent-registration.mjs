/**
 * Prebuild: rewrite apps/web/public/.well-known/agent-registration.json using the
 * same merge rules as apps/api/app/challenge/registration.py (Option B — API is
 * canonical at runtime; this keeps the static /.well-known copy aligned on Vercel).
 *
 * On Vercel (VERCEL=1): requires VITE_API_BASE_URL; web origin from
 * VERITRADE_PUBLIC_WEB_BASE_URL or Vercel system URLs.
 * Local: skips unless both VERITRADE_PUBLIC_WEB_BASE_URL and VITE_API_BASE_URL are set.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function stripSlash(s) {
  return s.replace(/\/+$/, "");
}

function webBase() {
  const explicit = (process.env.VERITRADE_PUBLIC_WEB_BASE_URL || "").trim();
  if (explicit) return stripSlash(explicit);
  if (process.env.VERCEL === "1") {
    if (process.env.VERCEL_ENV === "production") {
      const p = (process.env.VERCEL_PROJECT_PRODUCTION_URL || "").trim();
      if (p) return `https://${p}`;
    }
    const u = (process.env.VERCEL_URL || "").trim();
    if (u) return `https://${u}`;
  }
  return "";
}

function apiBase() {
  const v = (process.env.VITE_API_BASE_URL || "").trim();
  if (v) return stripSlash(v);
  const p = (process.env.VERITRADE_PUBLIC_API_BASE_URL || "").trim();
  if (p) return stripSlash(p);
  return "";
}

function agentRegistrationStaticUrl(web) {
  return `${web}/.well-known/agent-registration.json`;
}

function agentUriEffective(web, stub) {
  if (stub) return stub;
  return agentRegistrationStaticUrl(web);
}

function main() {
  const repoRoot = path.resolve(__dirname, "../../..");
  const specPath = path.join(repoRoot, "spec-alignment", "agent-registration.json");
  const outPath = path.join(__dirname, "../public/.well-known/agent-registration.json");

  const onVercel = process.env.VERCEL === "1";
  const web = webBase();
  const api = apiBase();

  if (!web || !api) {
    if (onVercel) {
      console.error(
        "sync-public-agent-registration: On Vercel, set VITE_API_BASE_URL to your public API base URL (https://…, no trailing slash). " +
          "Web origin is taken from VERITRADE_PUBLIC_WEB_BASE_URL, else VERCEL_PROJECT_PRODUCTION_URL (production) or VERCEL_URL (preview)."
      );
      process.exit(1);
    }
    console.log(
      "sync-public-agent-registration: skipping (not on Vercel). " +
        "For local refresh from .env, run from repo root: python scripts/export_agent_registration_static.py. " +
        "For a local production-style write here, set VERITRADE_PUBLIC_WEB_BASE_URL and VITE_API_BASE_URL."
    );
    process.exit(0);
  }

  const doc = JSON.parse(fs.readFileSync(specPath, "utf8"));

  doc.image = `${web}/veritrade-agent.svg`;
  doc.services = [
    { name: "web", endpoint: `${web}/`, version: "1.0.0" },
    { name: "http", endpoint: `${api}/docs`, version: "openapi" },
    { name: "http", endpoint: `${api}/challenge/context`, version: "1.0.0" },
    { name: "http", endpoint: `${api}/challenge/agent-registration`, version: "1.0.0" },
  ];

  const rid = (process.env.ERC8004_IDENTITY_REGISTRY_ADDRESS || "").trim();
  const aid = (process.env.ERC8004_ONCHAIN_AGENT_ID || "").trim();
  const stub = (process.env.ERC8004_AGENT_URI_STUB || "").trim();
  if (rid && aid) {
    const entry = { agentRegistry: rid, agentId: aid };
    const uriEff = agentUriEffective(web, stub);
    if (uriEff) entry.agentURI = uriEff;
    doc.registrations = [entry];
  } else {
    doc.registrations = [];
  }

  const wallet = (process.env.VERITRADE_AGENT_WALLET_PLACEHOLDER || "").trim();
  if (wallet) doc.agentWallet = wallet;
  else delete doc.agentWallet;

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, `${JSON.stringify(doc, null, 2)}\n`, "utf8");
  console.log("sync-public-agent-registration: wrote", outPath);
}

main();
