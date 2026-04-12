/**
 * Live operator soak: Kraken CLI tape + paper autonomous + lane metrics.
 *
 * Defaults (12 min spot, 12 min futures, 3 min general) — override for CI / dev:
 *   SOAK_SPOT_MS, SOAK_FUTURES_MS, SOAK_GENERAL_MS, SOAK_POLL_MS
 *
 * Requires API MARKET_DATA_MODE=kraken_cli and working KRAKEN_MARKET_CLI_* (no mock_fallback on snapshots).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, request as playwrightRequest } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESULT_DIR = path.join(__dirname, "../e2e-results");

const API_BASE =
  process.env.VITE_API_BASE_URL || process.env.VERITRADE_API_BASE_URL || "http://127.0.0.1:34120";

const SPOT_MS = Number(process.env.SOAK_SPOT_MS ?? 12 * 60 * 1000);
const FUTURES_MS = Number(process.env.SOAK_FUTURES_MS ?? 12 * 60 * 1000);
const GENERAL_MS = Number(process.env.SOAK_GENERAL_MS ?? 3 * 60 * 1000);
const POLL_MS = Number(process.env.SOAK_POLL_MS ?? 15_000);

type Paper = {
  filled_trades: number;
  blocked: number;
  skipped: number;
  reduced: number;
  review: number;
  equity: number | null;
  pnl_total: number | null;
  pnl_daily: number | null;
};

type Overview = {
  safety_strip?: { market_data_mode: string; market_mode_label: string };
  market_snapshot?: { source?: string; price?: number; captured_at?: string; symbol?: string } | null;
  cycle_history?: unknown[];
  autonomous?: {
    enabled: boolean;
    cadence_seconds: number;
    last_cycle_at?: string | null;
    next_cycle_at?: string | null;
    next_cycle_in_seconds?: number | null;
  };
  top_markets?: { symbol: string; price: number; captured_at?: string }[];
};

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function apiGet<T>(baseURL: string, path: string): Promise<T> {
  const ctx = await playwrightRequest.newContext({ baseURL });
  try {
    const res = await ctx.get(path);
    expect(res.ok(), `GET ${path} -> ${res.status()}`).toBeTruthy();
    return (await res.json()) as T;
  } finally {
    await ctx.dispose();
  }
}

async function apiPost(baseURL: string, path: string) {
  const ctx = await playwrightRequest.newContext({ baseURL });
  try {
    const res = await ctx.post(path);
    expect(res.ok(), `POST ${path} -> ${res.status()} ${await res.text().catch(() => "")}`).toBeTruthy();
    const txt = await res.text().catch(() => "");
    try {
      return txt ? JSON.parse(txt) : {};
    } catch {
      return {};
    }
  } finally {
    await ctx.dispose();
  }
}

async function activityCount(baseURL: string): Promise<number> {
  const rows = await apiGet<unknown[]>(baseURL, "/activity?limit=500");
  return rows.length;
}

async function snapshotMetrics(baseURL: string): Promise<{
  overview: Overview;
  paper: Paper;
  activityCount: number;
}> {
  const [overview, paper, activityCount_] = await Promise.all([
    apiGet<Overview>(baseURL, "/overview"),
    apiGet<Paper>(baseURL, "/viz/paper-session"),
    activityCount(baseURL),
  ]);
  return { overview, paper, activityCount: activityCount_ };
}

function assertLiveSnapshot(overview: Overview, label: string) {
  const mode = overview.safety_strip?.market_data_mode ?? "";
  const src = String(overview.market_snapshot?.source ?? "");
  expect(mode, `${label}: safety_strip.market_data_mode`).toBe("kraken_cli");
  expect(
    src.includes("mock_fallback"),
    `${label}: snapshot fell back to mock (${src}) — fix Kraken CLI template / binary`,
  ).toBe(false);
  expect(src.length, `${label}: empty snapshot source`).toBeGreaterThan(0);
}

function writeReport(name: string, body: Record<string, unknown>) {
  fs.mkdirSync(RESULT_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const file = path.join(RESULT_DIR, `${name}-${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify({ generatedAt: new Date().toISOString(), ...body }, null, 2), "utf8");
  fs.writeFileSync(path.join(RESULT_DIR, `${name}-latest.json`), JSON.stringify(body, null, 2), "utf8");
}

test.describe.configure({ mode: "serial" });

let liveKrakenSoak = false;

test.describe("Live paper soak (Kraken CLI)", () => {
  test.beforeAll(async () => {
    const overview = await apiGet<Overview>(API_BASE, "/overview");
    liveKrakenSoak = overview.safety_strip?.market_data_mode === "kraken_cli";
    if (liveKrakenSoak) assertLiveSnapshot(overview, "pre-soak");
  });

  test.beforeEach(({}, testInfo) => {
    if (!liveKrakenSoak) {
      testInfo.skip(true, `Soak requires MARKET_DATA_MODE=kraken_cli (restart API after updating root .env).`);
    }
  });

  test("Scenario 3 — general live surface (paper)", async ({ page }) => {
    test.setTimeout(GENERAL_MS + 120_000);
    await apiPost(API_BASE, "/lanes/spot_momentum/stop");
    await apiPost(API_BASE, "/lanes/futures_tactical/stop");
    await apiPost(API_BASE, "/control/autonomous/stop").catch(() => {});

    const before = await snapshotMetrics(API_BASE);
    const p0 = before.overview.top_markets?.find((r) => r.symbol === "BTCUSD")?.price ?? null;
    const c0 = before.overview.cycle_history?.length ?? 0;
    const a0 = before.activityCount;
    const mode0 = before.overview.safety_strip?.market_data_mode ?? "";

    await page.goto("/?mode=paper");
    await page.getByRole("button", { name: /Live Paper Trading/i }).click();
    await expect(page.getByTestId("market-data-mode")).toHaveText("kraken_cli");
    await page.getByTestId("autonomous-start-15").click();
    await expect(page.getByText(/Autonomous ON/i).first()).toBeVisible({ timeout: 60_000 });

    const samples: Record<string, unknown>[] = [];
    const end = Date.now() + GENERAL_MS;
    while (Date.now() < end) {
      await sleep(POLL_MS);
      const s = await snapshotMetrics(API_BASE);
      samples.push({
        t: new Date().toISOString(),
        btc: s.overview.top_markets?.find((r) => r.symbol === "BTCUSD")?.price,
        snapCap: s.overview.market_snapshot?.captured_at,
        cycles: s.overview.cycle_history?.length ?? 0,
        activity: s.activityCount,
        autoLast: s.overview.autonomous?.last_cycle_at,
      });
    }

    await page.getByTestId("autonomous-stop").click();
    await expect(page.getByText(/Autonomous idle/i).first()).toBeVisible({ timeout: 60_000 });

    const after = await snapshotMetrics(API_BASE);
    const p1 = after.overview.top_markets?.find((r) => r.symbol === "BTCUSD")?.price ?? null;
    const c1 = after.overview.cycle_history?.length ?? 0;
    const a1 = after.activityCount;
    const mode1 = after.overview.safety_strip?.market_data_mode ?? "";

    const priceMoved = p0 != null && p1 != null && p1 !== p0;
    const cyclesGrew = c1 > c0;
    const activityGrew = a1 > a0;

    writeReport("soak-general", {
      durationMs: GENERAL_MS,
      pollMs: POLL_MS,
      market_data_mode: mode1 || mode0,
      startBtcPrice: p0,
      endBtcPrice: p1,
      priceMoved,
      cycleHistoryStart: c0,
      cycleHistoryEnd: c1,
      cyclesGrew,
      activityStart: a0,
      activityEnd: a1,
      activityGrew,
      paperStart: {
        equity: before.paper.equity,
        pnl: before.paper.pnl_total,
        fills: before.paper.filled_trades,
        blocked: before.paper.blocked,
        skipped: before.paper.skipped,
        reduced: before.paper.reduced,
        review: before.paper.review,
      },
      paperEnd: {
        equity: after.paper.equity,
        pnl: after.paper.pnl_total,
        fills: after.paper.filled_trades,
        blocked: after.paper.blocked,
        skipped: after.paper.skipped,
        reduced: after.paper.reduced,
        review: after.paper.review,
      },
      samples,
    });

    expect
      .soft(cyclesGrew || activityGrew || priceMoved, "Expected cycle history, activity, or top-of-book to move during autonomous run")
      .toBeTruthy();
  });

  test("Scenario 1 — Spot lane autonomous soak", async ({ page }) => {
    test.setTimeout(SPOT_MS + 180_000);
    await apiPost(API_BASE, "/lanes/futures_tactical/stop");
    await apiPost(API_BASE, "/lanes/spot_momentum/start");
    await apiPost(API_BASE, "/control/autonomous/stop").catch(() => {});

    const start = await snapshotMetrics(API_BASE);
    assertLiveSnapshot(start.overview, "spot-start");

    await page.goto("/?mode=paper");
    await page.getByRole("button", { name: /Live Paper Trading/i }).click();
    await expect(page.getByTestId("lane-card-spot_momentum")).toBeVisible();

    await page.getByTestId("autonomous-start-15").click();
    await expect(page.getByText(/Autonomous ON/i).first()).toBeVisible({ timeout: 60_000 });

    const series: Record<string, unknown>[] = [];
    const end = Date.now() + SPOT_MS;
    let prevClose: string | null = null;
    let chartCloseChanged = false;
    while (Date.now() < end) {
      await sleep(POLL_MS);
      const snap = await snapshotMetrics(API_BASE);
      const lanesData = await apiGet<{ lane_id: string; performance: Record<string, number> }[]>(API_BASE, "/lanes");
      const spotLane = lanesData.find((l) => l.lane_id === "spot_momentum");
      const close = await page.getByTestId("chart-last-close").textContent().catch(() => null);
      if (close) {
        if (prevClose !== null && close.trim() !== prevClose.trim()) chartCloseChanged = true;
        prevClose = close.trim();
      }
      series.push({
        t: new Date().toISOString(),
        equity: snap.paper.equity,
        pnl: snap.paper.pnl_total,
        fills: snap.paper.filled_trades,
        blocked: snap.paper.blocked,
        skipped: snap.paper.skipped,
        reduced: snap.paper.reduced,
        review: snap.paper.review,
        cycles: snap.overview.cycle_history?.length ?? 0,
        activity: snap.activityCount,
        lanePnlTotal: spotLane?.performance?.pnl_total,
      });
    }

    await page.getByTestId("autonomous-stop").click();
    await expect(page.getByText(/Autonomous idle/i).first()).toBeVisible({ timeout: 60_000 });

    const final = await snapshotMetrics(API_BASE);
    await apiPost(API_BASE, "/lanes/spot_momentum/stop");

    const laneRow = (await apiGet<{ lane_id: string; performance: Record<string, number> }[]>(API_BASE, "/lanes")).find(
      (l) => l.lane_id === "spot_momentum",
    );

    writeReport("soak-spot", {
      lane: "spot_momentum",
      durationMs: SPOT_MS,
      start: {
        equity: start.paper.equity,
        pnl: start.paper.pnl_total,
        fills: start.paper.filled_trades,
        blocked: start.paper.blocked,
        skipped: start.paper.skipped,
        reduced: start.paper.reduced,
        review: start.paper.review,
      },
      end: {
        equity: final.paper.equity,
        pnl: final.paper.pnl_total,
        fills: final.paper.filled_trades,
        blocked: final.paper.blocked,
        skipped: final.paper.skipped,
        reduced: final.paper.reduced,
        review: final.paper.review,
        lanePnlTotal: laneRow?.performance?.pnl_total,
        laneEquity: laneRow?.performance?.equity,
      },
      chartCloseChanged,
      series,
    });

    expect(
      final.paper.filled_trades +
        final.paper.blocked +
        final.paper.skipped +
        final.paper.reduced +
        final.paper.review,
    ).toBeGreaterThanOrEqual(
      start.paper.filled_trades +
        start.paper.blocked +
        start.paper.skipped +
        start.paper.reduced +
        start.paper.review,
    );
  });

  test("Scenario 2 — Futures lane autonomous soak", async ({ page }) => {
    test.setTimeout(FUTURES_MS + 180_000);
    await apiPost(API_BASE, "/lanes/spot_momentum/stop");
    await apiPost(API_BASE, "/lanes/futures_tactical/start");
    await apiPost(API_BASE, "/control/autonomous/stop").catch(() => {});

    const start = await snapshotMetrics(API_BASE);
    assertLiveSnapshot(start.overview, "futures-start");

    await page.goto("/?mode=paper");
    await page.getByRole("button", { name: /Live Paper Trading/i }).click();
    await expect(page.getByTestId("lane-card-futures_tactical")).toBeVisible();

    await page.getByTestId("autonomous-start-15").click();
    await expect(page.getByText(/Autonomous ON/i).first()).toBeVisible({ timeout: 60_000 });

    const series: Record<string, unknown>[] = [];
    const end = Date.now() + FUTURES_MS;
    while (Date.now() < end) {
      await sleep(POLL_MS);
      const snap = await snapshotMetrics(API_BASE);
      series.push({
        t: new Date().toISOString(),
        equity: snap.paper.equity,
        pnl: snap.paper.pnl_total,
        fills: snap.paper.filled_trades,
        blocked: snap.paper.blocked,
        skipped: snap.paper.skipped,
        reduced: snap.paper.reduced,
        review: snap.paper.review,
        cycles: snap.overview.cycle_history?.length ?? 0,
        activity: snap.activityCount,
      });
    }

    await page.getByTestId("autonomous-stop").click();
    await expect(page.getByText(/Autonomous idle/i).first()).toBeVisible({ timeout: 60_000 });

    const final = await snapshotMetrics(API_BASE);
    await apiPost(API_BASE, "/lanes/futures_tactical/stop");

    const laneRow = (await apiGet<{ lane_id: string; performance: Record<string, number> }[]>(API_BASE, "/lanes")).find(
      (l) => l.lane_id === "futures_tactical",
    );

    writeReport("soak-futures", {
      lane: "futures_tactical",
      durationMs: FUTURES_MS,
      start: {
        equity: start.paper.equity,
        pnl: start.paper.pnl_total,
        fills: start.paper.filled_trades,
        blocked: start.paper.blocked,
        skipped: start.paper.skipped,
        reduced: start.paper.reduced,
        review: start.paper.review,
      },
      end: {
        equity: final.paper.equity,
        pnl: final.paper.pnl_total,
        fills: final.paper.filled_trades,
        blocked: final.paper.blocked,
        skipped: final.paper.skipped,
        reduced: final.paper.reduced,
        review: final.paper.review,
        lanePnlTotal: laneRow?.performance?.pnl_total,
        laneEquity: laneRow?.performance?.equity,
      },
      series,
    });

    expect(
      final.paper.filled_trades +
        final.paper.blocked +
        final.paper.skipped +
        final.paper.reduced +
        final.paper.review,
    ).toBeGreaterThanOrEqual(
      start.paper.filled_trades +
        start.paper.blocked +
        start.paper.skipped +
        start.paper.reduced +
        start.paper.review,
    );
  });
});
