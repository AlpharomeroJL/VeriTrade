import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadEnvIntoProcess() {
  const root = path.resolve(__dirname, "../..");
  const envPath = path.join(root, ".env");
  if (!fs.existsSync(envPath)) return root;
  const txt = fs.readFileSync(envPath, "utf8");
  for (const line of txt.split("\n")) {
    const m = line.match(/^\s*([^#=]+)=(.*)$/);
    if (m) process.env[m[1].trim()] = m[2].trim();
  }
  return root;
}

loadEnvIntoProcess();
const webPort = process.env.VERITRADE_WEB_PORT || "34110";
const baseURL = `http://127.0.0.1:${webPort}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  timeout: 90_000,
  expect: { timeout: 20_000 },
  use: {
    baseURL,
    trace: "on-first-retry",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", testIgnore: "**/soak*.spec.ts", use: { ...devices["Desktop Chrome"] } },
    {
      name: "chromium-soak",
      testMatch: "**/soak*.spec.ts",
      timeout: 1_200_000,
      expect: { timeout: 60_000 },
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "node ./e2e/serve-e2e.mjs",
    cwd: __dirname,
    url: `${baseURL}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
