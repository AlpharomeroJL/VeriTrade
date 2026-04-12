/**
 * Playwright webServer entry: ensure API is healthy, then start Vite.
 * Playwright sends SIGTERM when the run finishes; we forward that to children.
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const webDir = path.resolve(__dirname, "..");

function loadEnvFile() {
  const envPath = path.join(repoRoot, ".env");
  if (!fs.existsSync(envPath)) return;
  const txt = fs.readFileSync(envPath, "utf8");
  for (const line of txt.split("\n")) {
    const m = line.match(/^\s*([^#=]+)=(.*)$/);
    if (m) process.env[m[1].trim()] = m[2].trim();
  }
}

function httpOk(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(2500, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitUntil(url, { attempts = 120, delayMs = 500 } = {}) {
  for (let i = 0; i < attempts; i++) {
    if (await httpOk(url)) return;
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

const children = [];

function killChildren() {
  for (const c of children) {
    try {
      if (process.platform === "win32" && c.pid) {
        spawn("taskkill", ["/PID", String(c.pid), "/T", "/F"], { stdio: "ignore", shell: true });
      } else {
        c.kill("SIGTERM");
      }
    } catch {
      /* ignore */
    }
  }
}

function forwardShutdown() {
  killChildren();
  process.exit(0);
}

loadEnvFile();
const apiPort = process.env.VERITRADE_API_PORT || "34120";
const webPort = process.env.VERITRADE_WEB_PORT || "34110";
const healthUrl = `http://127.0.0.1:${apiPort}/health`;
const webUrl = `http://127.0.0.1:${webPort}/`;

const apiAlready = await httpOk(healthUrl);
if (!apiAlready) {
  const py = process.platform === "win32" ? "python" : process.env.PYTHON || "python3";
  const api = spawn(
    py,
    ["-m", "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "127.0.0.1", "--port", String(apiPort)],
    {
      cwd: repoRoot,
      stdio: "inherit",
      env: { ...process.env },
      shell: process.platform === "win32",
    },
  );
  children.push(api);
  await waitUntil(healthUrl);
}

const web = spawn("npm", ["run", "dev"], {
  cwd: webDir,
  stdio: "inherit",
  env: { ...process.env },
  shell: process.platform === "win32",
});
children.push(web);
await waitUntil(webUrl);

process.on("SIGINT", forwardShutdown);
process.on("SIGTERM", forwardShutdown);

await new Promise(() => {});
