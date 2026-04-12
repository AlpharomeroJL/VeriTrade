export type ProductMode = "guided" | "paper" | "watch";

export const PRODUCT_MODE_ORDER: ProductMode[] = ["guided", "paper", "watch"];

export const MODE_META: Record<
  ProductMode,
  { label: string; purpose: string; bestFor: string; anchor: string }
> = {
  guided: {
    label: "Guided Proof Demo",
    purpose: "Walk through a safe step-by-step example of how VeriTrade decides and records actions.",
    bestFor: "First run, judges, teaching the proof path",
    anchor: "vt-guided",
  },
  paper: {
    label: "Live Paper Trading",
    purpose: "Run the bot live against Kraken market tape using simulated execution.",
    bestFor: "Autonomous desk, lanes, session stats — fills stay simulated",
    anchor: "vt-paper",
  },
  watch: {
    label: "Market Watch",
    purpose: "Read the market, inspect trend and volatility, and understand what the bot is seeing.",
    bestFor: "Tape and context without running the full trading loop",
    anchor: "vt-watch",
  },
};
