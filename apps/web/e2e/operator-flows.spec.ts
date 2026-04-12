import { expect, test, type Page } from "@playwright/test";

test.describe.configure({ mode: "serial" });

/** Call before `goto`, then await after navigation, so the first GET /overview is captured. */
function overviewResponsePromise(page: Page) {
  return page.waitForResponse(
    (r) => r.url().includes("/overview") && r.request().method() === "GET" && r.status() === 200,
    { timeout: 60_000 },
  );
}

test.describe("VeriTrade operator flows", () => {
  test("core smoke: shell, mode switcher, chart host, no degraded banner", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "VeriTrade", level: 1 })).toBeVisible();
    await expect(page.getByRole("banner")).toContainText("VeriTrade");
    await expect(page.getByTestId("product-mode-switcher")).toBeVisible();
    await expect(page.getByRole("button", { name: /Guided Proof Demo/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Live Paper Trading/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Market Watch/i })).toBeVisible();
    await expect(page.locator(".vt-chart-host").or(page.getByText(/Loading candles/i))).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Degraded", { exact: true })).not.toBeVisible();
  });

  test("guided: quick start, seed, run cycle, proof trail, plain-English story", async ({ page }) => {
    const overviewWait = overviewResponsePromise(page);
    await page.goto("/");
    await overviewWait;
    await expect(page.getByText("Quick start", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: /Guided Proof Demo/i }).click();
    await expect(page.getByRole("heading", { name: /Four steps to learn the console/i })).toBeVisible();

    const seed = page.getByRole("button", { name: "Seed demo data" });
    const runOnce = page.getByRole("button", { name: "Run one cycle" });
    const openTrail = page.getByRole("button", { name: /Open proof trail/i });
    await expect(seed.or(runOnce).or(openTrail)).toBeVisible({ timeout: 60_000 });

    if (await seed.isVisible()) {
      await seed.click();
      await expect(seed).toBeEnabled({ timeout: 60_000 });
    }
    if (await runOnce.isVisible()) {
      await runOnce.click();
      await expect(runOnce).toBeEnabled({ timeout: 60_000 });
    }

    const trail = page.locator("#proof-trail");
    await expect(trail).toBeVisible();
    await expect(trail.getByRole("listitem")).not.toHaveCount(0, { timeout: 30_000 });

    await page.locator("details").filter({ hasText: "Pipeline, lanes, desk tools" }).click();
    await expect(page.getByText("Why the bot did this").first()).toBeVisible();
    await expect(page.getByText("What the tape showed").first()).toBeVisible();
  });

  test("watch: hero chart, top pairs strip, Kraken launch cards", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Market Watch/i }).click();
    await expect(page.getByRole("region", { name: "Live market chart" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Tape · markers · timeframes|Price chart · timeframes · markers|OHLC/i }),
    ).toBeVisible();
    await expect(page.getByRole("region", { name: "Top pairs" })).toBeVisible();
    await expect(page.getByText(/BTC\/USD, ETH\/USD, SOL\/USD/i).first()).toBeVisible();
    await expect(page.getByTestId("kraken-launch-sessions")).toBeVisible();
    await expect(page.getByRole("button", { name: "Launch" }).first()).toBeVisible();
    await expect(page.getByText("Morning Brief")).toBeVisible();
    await expect(page.getByText("Watch Market")).toBeVisible();
  });

  test("paper: autonomous controls, lanes, start/stop 15s", async ({ page }) => {
    const overviewWait = overviewResponsePromise(page);
    await page.goto("/");
    await overviewWait;
    await page.getByRole("button", { name: /Live Paper Trading/i }).click();
    const auto15 = page.getByTestId("autonomous-start-15");
    await expect(page.getByTestId("live-paper-hero-rail")).toBeVisible({ timeout: 60_000 });
    await expect(auto15).toBeAttached({ timeout: 60_000 });
    await auto15.scrollIntoViewIfNeeded();
    await expect(auto15).toBeVisible();
    await expect(page.getByTestId("trading-lanes-panel")).toBeVisible();

    await auto15.click();
    await expect(page.getByText(/Autonomous ON/i).first()).toBeVisible({ timeout: 25_000 });
    await expect(page.getByText("Running").first()).toBeVisible();

    await page.waitForTimeout(2500);

    const autoStop = page.getByTestId("autonomous-stop");
    await autoStop.scrollIntoViewIfNeeded();
    await autoStop.click();
    await expect(autoStop).toBeEnabled({ timeout: 60_000 });
    await expect(page.getByText(/Autonomous idle/i).first()).toBeVisible({ timeout: 25_000 });
    await expect(page.locator("section:has(#autonomous-heading)").getByText("Idle", { exact: true })).toBeVisible();
  });

  test("paper: spot and futures lane run-once", async ({ page }) => {
    const overviewWait = overviewResponsePromise(page);
    await page.goto("/");
    await overviewWait;
    await page.getByRole("button", { name: /Live Paper Trading/i }).click();
    await expect(page.getByTestId("live-paper-hero-rail")).toBeVisible({ timeout: 60_000 });
    const spotRun = page.getByTestId("lane-run-once-spot_momentum");
    await expect(spotRun).toBeAttached({ timeout: 60_000 });
    await spotRun.scrollIntoViewIfNeeded();
    await spotRun.click();
    await expect(spotRun).toBeEnabled({ timeout: 60_000 });

    const futRun = page.getByTestId("lane-run-once-futures_tactical");
    await futRun.scrollIntoViewIfNeeded();
    await futRun.click();
    await expect(futRun).toBeEnabled({ timeout: 60_000 });
  });

  test("paper: command bar Run cycle re-enables quickly (no stuck busy)", async ({ page }) => {
    const overviewWait = overviewResponsePromise(page);
    await page.goto("/?mode=paper");
    await overviewWait;
    await page.getByRole("button", { name: /Live Paper Trading/i }).click();
    await expect(page.getByTestId("live-paper-hero-rail")).toBeVisible({ timeout: 60_000 });
    const run = page.getByRole("button", { name: "Run cycle" });
    await expect(run).toBeAttached({ timeout: 60_000 });
    await run.scrollIntoViewIfNeeded();
    await expect(run).toBeVisible();
    await run.click();
    await expect(run).toBeEnabled({ timeout: 20_000 });
  });

  test("paper: scenario presets under More tools", async ({ page }) => {
    const overviewWait = overviewResponsePromise(page);
    await page.goto("/?mode=paper");
    await overviewWait;
    await page.getByRole("button", { name: /Live Paper Trading/i }).click();
    await expect(page.getByTestId("live-paper-hero-rail")).toBeVisible({ timeout: 60_000 });
    const moreTools = page.locator("details").filter({ hasText: "Scenarios, lane rationale" });
    await expect(moreTools).toBeAttached({ timeout: 60_000 });
    await moreTools.scrollIntoViewIfNeeded();
    await moreTools.click();
    const presets = page.locator("#scenario-presets");
    await expect(presets).toBeVisible();
    const safeBtn = presets.getByRole("button", { name: /Safe market → allow/i });
    await safeBtn.click();
    await expect(safeBtn).toBeEnabled({ timeout: 60_000 });
  });

  test("scenario presets: distinct readouts", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Guided Proof Demo/i }).click();

    const presets = page.locator("#scenario-presets");
    const safeBtn = presets.getByRole("button", { name: /Safe market → allow/i });
    const volatileBtn = presets.getByRole("button", { name: /Volatile → block/i });
    const oversizedBtn = presets.getByRole("button", { name: /Oversized → trim/i });

    await safeBtn.click();
    await expect(safeBtn).toBeEnabled({ timeout: 60_000 });
    await expect(page.getByTestId("scenario-outcome-headline")).toContainText(/allow|fill|approved/i, { timeout: 15_000 });

    await volatileBtn.click();
    await expect(volatileBtn).toBeEnabled({ timeout: 60_000 });
    await expect(page.getByTestId("scenario-outcome-headline")).toContainText(/block|blocked/i);

    await oversizedBtn.click();
    await expect(oversizedBtn).toBeEnabled({ timeout: 60_000 });
    await expect(page.getByTestId("scenario-outcome-headline")).toContainText(/trim|reduced|smaller|reduction/i);
  });

  test("chart: timeframes and clock toggle", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Guided Proof Demo/i }).click();
    const seed = page.getByRole("button", { name: "Seed demo data" });
    if (await seed.isVisible()) {
      await seed.click();
      await expect(seed).toBeEnabled({ timeout: 60_000 });
    }
    await expect(page.getByText("Timeframe", { exact: false })).toBeVisible();
    await expect(page.locator(".vt-chart-host")).toBeVisible({ timeout: 60_000 });

    await page.getByRole("button", { name: "5m", exact: true }).click();
    await expect(page.locator(".vt-chart-host")).toBeVisible();
    await page.getByRole("button", { name: "15m", exact: true }).click();
    await expect(page.locator(".vt-chart-host")).toBeVisible();
    await page.getByRole("button", { name: "1m", exact: true }).click();
    await expect(page.locator(".vt-chart-host")).toBeVisible();

    await page.getByRole("button", { name: "UTC", exact: true }).click();
    await expect(page.getByRole("region", { name: "Live market chart" })).toBeVisible();
    await page.getByRole("button", { name: "Local", exact: true }).click();
    await expect(page.getByRole("region", { name: "Live market chart" })).toBeVisible();
  });

  test("proof trail: expand raw details", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Guided Proof Demo/i }).click();
    const seed = page.getByRole("button", { name: "Seed demo data" });
    const runOnce = page.getByRole("button", { name: "Run one cycle" });
    const openTrail = page.getByRole("button", { name: /Open proof trail/i });
    await expect(seed.or(runOnce).or(openTrail)).toBeVisible({ timeout: 60_000 });
    if (await seed.isVisible()) {
      await seed.click();
      await expect(seed).toBeEnabled({ timeout: 60_000 });
    }
    if (await runOnce.isVisible()) {
      await runOnce.click();
      await expect(runOnce).toBeEnabled({ timeout: 60_000 });
    }

    const trail = page.locator("#proof-trail");
    await expect(trail.getByRole("listitem").first()).toBeVisible();
    await trail.getByText("Raw record (JSON / technical)").first().click();
    await expect(trail.locator("pre").first()).toBeVisible();

    await page.locator("details").filter({ hasText: "Pipeline, lanes, desk tools" }).click();
    await expect(page.getByRole("heading", { name: "Decision pipeline", exact: true })).toBeVisible();
  });
});
