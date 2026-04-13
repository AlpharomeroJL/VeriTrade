import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ProductMode } from "./dashboard/modeCopy";
import { SectionHead } from "./dashboard/SectionHead";
import { tapeSourceLabel } from "./dashboard/tapeSource";
import { TopPairsStrip } from "./dashboard/panels/TopPairsStrip";
import { Badge, surfaceClass, Tip } from "./dashboard/uiPrimitives";
import { GuidedDemoSteps } from "./modes/GuidedDemoSteps";
import { EvidenceCollapsible } from "./modes/EvidenceCollapsible";
import { GlobalShell } from "./shell/GlobalShell";
import { api, postJson } from "./api";
import { LiveCandleChart, type Candle, type ChartIntervalId, type ChartMarker } from "./LiveCandleChart";
import { formatOperatorTimestamp, TIME_DISPLAY_STORAGE_KEY, type TimeDisplayMode } from "./operatorTime";
import { getGuidance, quickStartActiveStep, type Guidance, type GuidanceAction } from "./dashboard/guidance";
import {
  activityExplanation,
  activityHeadline,
  artifactNarrativeLines,
  type ArtifactKind,
  type OverviewLike,
  type PipelineStageKind,
  type PipelineVisualState,
  pipelineStageSummary,
  pipelineStageVisualState,
  pipelineWhatHappenedPlain,
  pipelineStagePlainExplain,
  proofTrailStageLabel,
  stageChallengeSubtitle,
  stagePublicTitle,
} from "./dashboard/summaries";

function chartIntervalLabel(id: ChartIntervalId): string {
  switch (id) {
    case "1m":
      return "1-minute";
    case "5m":
      return "5-minute";
    case "15m":
      return "15-minute";
    case "30m":
      return "30-minute";
    case "1h":
      return "1-hour";
    default:
      return id;
  }
}

const CHART_INTERVAL_IDS: ChartIntervalId[] = ["1m", "5m", "15m", "30m", "1h"];

function coerceChartInterval(v: unknown, fallback: ChartIntervalId): ChartIntervalId {
  const s = typeof v === "string" ? v.trim().toLowerCase() : "";
  return CHART_INTERVAL_IDS.includes(s as ChartIntervalId) ? (s as ChartIntervalId) : fallback;
}

function truncSilent(s: string, max: number): string {
  const t = s.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

/** One sentence for silent demo — latest anchored cycle only */
function livePaperCurrentStorySentence(o: Overview | null): string {
  if (!o?.latest_risk && !o?.latest_signal) {
    return "Waiting for desk data — use Run cycle, a lane run, or autonomous mode so this line can describe the latest decision.";
  }
  const sig = o.latest_signal as Record<string, unknown> | null | undefined;
  const risk = o.latest_risk as Record<string, unknown> | null | undefined;
  const ex = o.latest_execution as Record<string, unknown> | null | undefined;
  const verdict = str(risk?.verdict) ?? "";
  const asset = str(sig?.asset) ?? "this pair";
  const idea = str(sig?.signal_type) ?? "an action";
  const snap = o.market_snapshot;
  const vol = snap && typeof snap === "object" && snap.volatility_flag === true;
  const tape = vol ? "Volatile tape" : "Calm tape";
  const exs = str(ex?.status);

  if (verdict === "block") {
    if ((str(risk?.reasons) ?? "").toLowerCase().includes("duplicate_action")) {
      return `${tape}; the desk proposed ${idea} on ${asset}; duplicate guard blocked a repeat — no trade placed.`;
    }
    return `${tape}; the bot proposed ${idea} on ${asset}; risk blocked it — no trade placed.`;
  }
  if (verdict === "skip") {
    return `${tape}; weak or neutral setup — the system stood aside this cycle (no trade).`;
  }
  if (verdict === "escalate_for_review") {
    return `${tape}; the bot proposed ${idea}; risk queued it for operator review — no automatic fill.`;
  }
  if (verdict === "allow_with_reduction") {
    if (exs === "filled") return `${tape}; market aligned; risk trimmed size; a paper fill was recorded for ${asset}.`;
    return `${tape}; market aligned; risk approved a reduced size — execution ${exs || "pending or not filled yet"}.`;
  }
  if (verdict === "allow") {
    if (exs === "filled") return `${tape}; risk cleared the idea; a paper fill was recorded for ${asset}.`;
    return `${tape}; risk cleared the idea — execution ${exs || "pending"}.`;
  }
  return `${tape}; latest safety state is ${verdict || "—"} on ${asset}.`;
}

function LivePaperHeroStatusRail({
  safetyStrip,
  autonomous,
  laneScopeLabel,
  lastRefreshedAtIso,
  tapeCapturedAt,
  timeDisplay,
}: {
  safetyStrip: SafetyStrip | null | undefined;
  autonomous: AutonomousStatus | null | undefined;
  laneScopeLabel: string;
  lastRefreshedAtIso: string | null;
  tapeCapturedAt: string | null | undefined;
  timeDisplay: TimeDisplayMode;
}) {
  const s = safetyStrip;
  const auto = autonomous;
  if (!s) return null;
  return (
    <div
      data-testid="live-paper-hero-rail"
      className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-white/[0.07] bg-gradient-to-r from-black/50 via-[#0a1018]/90 to-black/40 px-4 py-3 ring-1 ring-teal-500/10 sm:px-5"
      aria-label="Desk status"
    >
      <span className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-600">Desk</span>
      <Badge
        data-testid="hero-rail-market-source"
        label={s.market_mode_label}
        tone={s.market_data_mode === "demo" ? "slate" : "sky"}
      />
      <Badge label={s.execution_mode} tone="indigo" />
      <Badge label={auto?.enabled ? `Autonomous ON · ${auto.cadence_seconds}s` : "Autonomous idle"} tone={auto?.enabled ? "emerald" : "slate"} />
      <Badge label={laneScopeLabel} tone="violet" />
      {lastRefreshedAtIso ? (
        <span className="font-mono text-[10px] text-slate-500">Ref {formatOperatorTimestamp(lastRefreshedAtIso, timeDisplay)}</span>
      ) : null}
      {tapeCapturedAt ? (
        <span data-testid="hero-rail-tape" className="font-mono text-[10px] text-slate-500">
          Tape {formatOperatorTimestamp(tapeCapturedAt, timeDisplay)}
        </span>
      ) : null}
    </div>
  );
}

function LivePaperDecisionStack({
  story,
  marketLine,
  botLine,
  riskLine,
  execLine,
  reasonLine,
  cycleDelta,
  riskClassName,
  execClassName,
}: {
  story: string;
  marketLine: string;
  botLine: string;
  riskLine: string;
  execLine: string;
  reasonLine: string;
  cycleDelta: string;
  riskClassName: string;
  execClassName: string;
}) {
  const block =
    "rounded-xl border border-white/[0.06] bg-gradient-to-b from-white/[0.04] to-black/20 px-4 py-4 ring-1 ring-white/[0.04] sm:px-5 sm:py-4";
  const lab = "text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500";
  const val = "mt-1.5 text-[15px] font-semibold leading-snug text-slate-50 sm:text-base";
  return (
    <div
      className="flex min-h-0 flex-col gap-4"
      aria-label="Current decision cycle"
    >
      <div
        className="rounded-2xl border border-teal-500/30 bg-[#060b14]/95 px-4 py-4 shadow-[0_12px_40px_-16px_rgba(0,0,0,0.9)] ring-1 ring-teal-500/15 sm:px-5 sm:py-5"
        aria-live="polite"
      >
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-teal-400/90">Current story</p>
        <p className="mt-2 text-base font-medium leading-relaxed text-slate-100 sm:text-lg">{story}</p>
      </div>

      <div className={block}>
        <p className={lab}>Market state</p>
        <p className={val}>{marketLine}</p>
      </div>
      <div className={block}>
        <p className={lab}>Bot idea</p>
        <p className={val}>{botLine}</p>
      </div>
      <div className={block}>
        <p className={lab}>Risk verdict</p>
        <p className={`${val} ${riskClassName}`}>{riskLine}</p>
      </div>
      <div className={block}>
        <p className={lab}>Execution</p>
        <p className={`${val} ${execClassName}`}>{execLine}</p>
      </div>
      <div className={`${block} border-white/[0.05]`}>
        <p className={lab}>Policy line</p>
        <p className="mt-1.5 text-sm leading-snug text-slate-400">{reasonLine}</p>
      </div>

      <details className="group rounded-xl border border-white/[0.05] bg-black/25 px-4 py-3 ring-1 ring-white/[0.04]">
        <summary className="cursor-pointer list-none text-[10px] font-semibold uppercase tracking-wider text-slate-600 marker:content-none [&::-webkit-details-marker]:hidden">
          <span className="text-slate-500 group-open:text-teal-400/80">Tape read · markers</span>
          <span className="ml-2 text-slate-700">▾</span>
        </summary>
        <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
          <span className="text-emerald-400/90">▲</span> buy ·<span className="text-sky-400/90"> ▼</span> sell ·<span className="text-rose-400/90"> ●</span> blocked ·
          <span className="text-amber-400/90"> ●</span> reduced ·<span className="text-violet-400/90"> ■</span> review · OHLC markers snap to the bar where the desk logged.
        </p>
      </details>

      <div className="rounded-xl border border-teal-500/15 bg-teal-950/15 px-4 py-3 ring-1 ring-teal-500/10">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-teal-500/80">What changed</p>
        <p className="mt-1.5 text-sm leading-snug text-slate-400">{cycleDelta}</p>
      </div>
    </div>
  );
}

type Erc8004DraftSurfaces = {
  eip_draft_url: string;
  alignment: string;
  identity_registry: string;
  agent_uri_effective: string | null;
  agent_registration_url: string;
  agent_registration_static_url: string;
  agent_wallet_placeholder: string | null;
  on_chain_validation_attested: boolean;
  intent_binding_scheme: string;
  validation_request_hash_algorithm: string;
};

type ChallengeContext = {
  agent_id: string;
  erc8004_agent_uri_stub: string | null;
  erc8004_draft: Erc8004DraftSurfaces;
  policy_version: string;
  intent_commitment_algorithm: string;
  trust_signals: string[];
  kraken_surface: {
    routing_mode: string;
    active_execution_provider: string;
    kraken_execution_enabled_flag: boolean;
    allow_real_orders: boolean;
    cli_command_stub: string;
    note: string;
    latest_order_draft: Record<string, unknown> | null;
  };
};

type RubricMetrics = {
  validation_artifact_count: number;
  risk_full_allow_count: number;
  risk_reduced_count: number;
  risk_allow_or_trim_count: number;
  risk_block_count: number;
  risk_skip_count: number;
  trust_score_0_100: number;
  trust_posture_label: string;
  trust_score_explainer: string;
};

type SafetyStrip = {
  market_data_mode: string;
  market_mode_label: string;
  market_data_detail: string;
  execution_mode: string;
  paper_safe_execution: boolean;
  live_trading_enabled: boolean;
  risk_router_active: boolean;
  validation_artifacts_active: boolean;
};

type TopMarketRow = {
  symbol: string;
  price: number;
  bid: number | null;
  ask: number | null;
  source: string;
  captured_at: string;
};

type AutonomousStatus = {
  enabled: boolean;
  cadence_seconds: number;
  last_cycle_at: string | null;
  next_cycle_at: string | null;
  next_cycle_in_seconds: number | null;
};

type CycleHistoryItem = {
  timestamp: string;
  outcome: "allowed" | "reduced" | "blocked" | "skipped" | "review" | "error" | string;
  verdict: string | null;
  execution_status: string | null;
  note: string;
  lane_id?: string | null;
  lane_label?: string | null;
  detail?: string | null;
  detail_technical?: string | null;
};

type ChallengeFit = {
  kraken_execution_surface_aligned: boolean;
  erc8004_identity_hooks: boolean;
  erc8004_agent_registration_available: boolean;
  combined_submission_story: boolean;
  paper_safe_demo_mode: boolean;
  risk_router_active: boolean;
  validation_artifacts_active: boolean;
};

type Overview = OverviewLike & {
  control: {
    mode: string;
    manual_pause: boolean;
    no_trade: boolean;
    trading_mode: string;
    execution_provider: string;
  };
  challenge: ChallengeContext;
  rubric_metrics: RubricMetrics;
  challenge_fit: ChallengeFit;
  safety_strip: SafetyStrip;
  autonomous: AutonomousStatus;
  cycle_history: CycleHistoryItem[];
  lane_trust?: LaneTrustSummary[];
  top_markets: TopMarketRow[];
  latest_performance: Record<string, unknown> | null;
  market_snapshot: Record<string, unknown> | null;
};

const SCENARIO_PRESETS: { id: string; label: string; hint: string }[] = [
  { id: "safe_allow", label: "Safe market → allow", hint: "Calm tape, room on the book — expect a full allow through paper execution." },
  { id: "volatile_block", label: "Volatile → block", hint: "Elevated vol flag — risk router stops before intent." },
  { id: "oversized_reduce", label: "Oversized → trim", hint: "Tight position headroom — expect allow_with_reduction and a smaller approved size." },
];

const SCENARIO_MESSAGES: Record<string, string> = {
  safe_allow: "Safe market → allowed trade",
  volatile_block: "Volatile market → blocked at risk",
  oversized_reduce: "Oversized request → reduced approval",
};

type ActivityItem = {
  id: number;
  kind: string;
  timestamp: string;
  summary: string;
  verdict_or_status: string | null;
  related_id: string | null;
};

type KrakenSkillSession = {
  id: number;
  session_type: "market_brief" | "monitoring" | "paper_trading" | "alert" | string;
  operation: string;
  symbols: string[];
  started_at: string;
  ended_at: string | null;
  status: string;
  logs: { at?: string; message?: string }[];
  outputs: Record<string, unknown>;
  summary: string;
  metrics: Record<string, unknown>;
  rationale: string;
};

type TradingLane = {
  lane_id: string;
  lane_label: string;
  market_type: string;
  strategy_family: string;
  default_symbols: string[];
  capital_allocation: number;
  risk_profile: string;
  cadence_seconds: number;
  status: string;
  last_outcome: string;
  performance: {
    equity: number;
    pnl_total: number;
    drawdown: number;
    open_notional: number;
    allow_count: number;
    reduce_count: number;
    block_count: number;
    skip_count: number;
  };
};

type LaneTrustSummary = {
  lane_id: string;
  lane_label: string;
  market_type: string;
  allow_count: number;
  reduce_count: number;
  block_count: number;
  review_count: number;
  stand_aside_count?: number;
  artifact_count?: number;
  trust_score_0_100: number;
  posture_label: string;
  explainer_one_liner: string;
};

type MarketChartContext = {
  trend: string;
  momentum: string;
  volatility: string;
  ma_short: number;
  ma_long: number;
  momentum_pct_10m: number;
  candle_count: number;
  source: string;
  what_the_bot_saw: string[];
  trade_hint: string;
};

type MarketChartPack = {
  symbol: string;
  interval?: string;
  candles: Candle[];
  points: { t: string; price: number }[];
  markers: ChartMarker[];
  context: MarketChartContext | null;
};

type PaperSession = {
  filled_trades: number;
  blocked: number;
  skipped: number;
  reduced: number;
  review: number;
  allow_full: number;
  equity: number | null;
  pnl_total: number | null;
  pnl_daily: number | null;
  position_notional: number | null;
  best_win_label: string | null;
  worst_loss_label: string | null;
  session_story: string;
};

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function num(v: unknown): number | undefined {
  return typeof v === "number" && !Number.isNaN(v) ? v : undefined;
}

const fmtUsd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const PIPELINE_KINDS: PipelineStageKind[] = ["signal", "risk", "intent", "execution"];

const ARTIFACT_ORDER = ["signal", "risk", "intent", "execution"] as const;

function riskTone(verdict: string): "emerald" | "sky" | "rose" | "violet" | "slate" {
  if (verdict === "allow") return "emerald";
  if (verdict === "allow_with_reduction") return "sky";
  if (verdict === "skip") return "sky";
  if (verdict === "block") return "rose";
  if (verdict === "escalate_for_review") return "violet";
  return "slate";
}

function execTone(status: string): "emerald" | "rose" | "slate" {
  if (status === "filled") return "emerald";
  if (status === "rejected") return "rose";
  return "slate";
}

function modeValueClass(mode: string): string {
  if (mode === "running") return "text-emerald-200";
  if (mode === "paused") return "text-amber-200";
  if (mode === "stopped") return "text-rose-200";
  return "text-white";
}

function riskValueClass(verdict: string): string {
  if (verdict === "allow") return "text-emerald-200";
  if (verdict === "allow_with_reduction") return "text-sky-200";
  if (verdict === "skip") return "text-sky-200";
  if (verdict === "block") return "text-rose-200";
  if (verdict === "escalate_for_review") return "text-violet-200";
  return "text-slate-100";
}

function execValueClass(status: string): string {
  if (status === "filled") return "text-emerald-200";
  if (status === "rejected") return "text-rose-200";
  return "text-slate-100";
}

function simpleBotStoryLines(overview: Overview | null, chartContext: MarketChartContext | null): { title: string; body: string }[] {
  if (!overview?.latest_signal && !overview?.latest_risk) {
    return [
      {
        title: "Start here",
        body: "Tap “Seed demo data” above. Then you’ll see what the bot noticed, what it tried to do, and whether safety allowed it — all in normal words.",
      },
    ];
  }
  const sig = overview.latest_signal;
  const risk = overview.latest_risk;
  const intent = overview.latest_intent;
  const ex = overview.latest_execution;
  const market = overview.market_snapshot;
  const asset = str(sig?.asset) ?? str(intent?.asset) ?? "this market";
  const proposed = str(sig?.signal_type) ?? "—";
  const conf = num(sig?.confidence);
  const verdict = str(risk?.verdict) ?? "—";
  const price =
    market && typeof market === "object" ? num(market.price) : undefined;
  const vol = market && typeof market === "object" && market.volatility_flag === true;

  const candlePreamble =
    chartContext?.what_the_bot_saw?.length ?
      `${chartContext.what_the_bot_saw.slice(0, 4).join(" ")} `
    : "";

  const saw =
    price != null
      ? `${candlePreamble}We also saved a fresh ticker-style price for ${asset} (about ${price.toLocaleString()}). ${vol ? "That snapshot’s spread flagged as jumpy." : "That snapshot looked steady."}`
      : `${candlePreamble}We had a trading idea for ${asset}, but no fresh price snapshot is on screen yet.`;

  const hintTail = chartContext?.trade_hint ? ` ${chartContext.trade_hint}` : "";

  const wanted =
    proposed !== "—"
      ? `The bot’s idea was “${proposed}” on ${asset}${conf != null ? `, with about ${Math.round(conf * 100)}% confidence` : ""}. That is only a suggestion until safety checks run.`
      : "The bot had not finished spelling out a clear action yet.";

  let safety = "";
  if (verdict === "block") {
    safety = "Risk blocked this idea — no signed intent and no paper fill on this cycle.";
  } else if (verdict === "skip") {
    safety =
      "The desk stood aside this cycle (no entry). That is a passive no-trade, not the same as a hard block — no intent and no fill.";
  } else if (verdict === "escalate_for_review") {
    safety = "Risk escalated for operator review — no automatic paper fill until that clears.";
  } else if (verdict === "allow_with_reduction") {
    safety = `The safety checker said yes, but only with a smaller size than requested — like only letting you spend part of your allowance.${hintTail}`;
  } else if (verdict === "allow") {
    safety = `The safety checker said yes under the current rules (still paper money only).${hintTail}`;
  } else {
    safety = `Safety status: ${verdict}.${hintTail}`;
  }

  let next = "";
  if (verdict === "block" || verdict === "escalate_for_review") {
    next = "Nothing executed automatically — the run stops at safety. Use the proof trail below for timestamps and payloads.";
  } else if (verdict === "skip") {
    next = "Passive cycle — the decision is on the ledger; no signed intent for this step.";
  } else if (ex?.status === "filled") {
    next = "A paper fill was recorded at the reference price. Chart and performance tiles update here — no venue orders.";
  } else if (ex?.status === "rejected") {
    next = "Paper execution said no (for example zero size). The book stayed flat.";
  } else {
    next = "Next step: wait for execution to show up, or run another cycle.";
  }

  const bottom =
    verdict === "block"
      ? "Bottom line: the bot noticed something, but safety kept the account out of trouble."
      : verdict === "skip"
        ? "Bottom line: no trade by design this cycle — do not read that as a red-light block unless you also see verdict block."
        : ex?.status === "filled"
        ? "Bottom line: idea → safety → signed plan → simulated fill — all on the ledger for this run."
        : "Bottom line: you can read the whole story without knowing trading jargon.";

  return [
    { title: "What the tape showed", body: saw },
    { title: "What it proposed", body: wanted },
    { title: "What risk decided", body: safety },
    { title: "What happened next", body: next },
    { title: "Bottom line", body: bottom },
  ];
}

function AutonomousStatePanel({
  overview,
  paperSession,
  busy,
  onAction,
  emphasize,
  timeDisplay,
  variant = "full",
  sectionId,
  layout = "default",
}: {
  overview: Overview | null;
  paperSession: PaperSession | null;
  busy: string | null;
  onAction: (label: string, path: string) => void;
  emphasize: boolean;
  timeDisplay: TimeDisplayMode;
  variant?: "full" | "readonly";
  sectionId?: string;
  layout?: "default" | "compact";
}) {
  const auto = overview?.autonomous;
  const s = overview?.safety_strip;
  const rm = overview?.rubric_metrics;
  if (!auto || !s) return null;
  const alive = auto.enabled;
  if (layout === "compact" && variant === "full") {
    return (
      <section
        id={sectionId}
        className={`${surfaceClass("")} scroll-mt-24 overflow-hidden ${emphasize ? "ring-1 ring-teal-500/25" : ""}`}
        aria-labelledby="autonomous-heading"
      >
        <div className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="min-w-0">
            <p id="autonomous-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
              Autonomous loop
            </p>
            <p className={`mt-1 text-2xl font-semibold ${alive ? "text-emerald-200" : "text-slate-400"}`}>{alive ? "Running" : "Idle"}</p>
            <p className="mt-1 font-mono text-[11px] text-slate-500">
              Last{" "}
              <span data-testid="autonomous-last-cycle-at">
                {auto.last_cycle_at ? formatOperatorTimestamp(auto.last_cycle_at, timeDisplay) : "—"}
              </span>
              {" · "}
              Next{" "}
              <span data-testid="autonomous-next-cycle-at">
                {auto.next_cycle_at ? formatOperatorTimestamp(auto.next_cycle_at, timeDisplay) : "—"}
                {alive && auto.next_cycle_in_seconds != null ? ` · in ${auto.next_cycle_in_seconds}s` : ""}
              </span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              data-testid="autonomous-start-15"
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-40"
              disabled={!!busy}
              onClick={() => onAction("auto-start-15", "/control/autonomous/start?cadence_seconds=15")}
            >
              Start 15s
            </button>
            <button
              type="button"
              data-testid="autonomous-start-30"
              className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:opacity-40"
              disabled={!!busy}
              onClick={() => onAction("auto-start-30", "/control/autonomous/start?cadence_seconds=30")}
            >
              Start 30s
            </button>
            <button
              type="button"
              data-testid="autonomous-stop"
              className="rounded-lg px-4 py-2 text-sm font-semibold text-rose-300 transition hover:bg-rose-500/10 hover:text-rose-200 disabled:opacity-40"
              disabled={!!busy}
              onClick={() => onAction("auto-stop", "/control/autonomous/stop")}
            >
              Stop
            </button>
          </div>
        </div>
        <div className="grid gap-3 border-t border-white/[0.04] px-5 py-3 sm:grid-cols-3 sm:px-6">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Session PnL</p>
            <p data-testid="paper-metric-pnl-total" className="mt-1 text-lg font-semibold tabular-nums text-white">
              {paperSession?.pnl_total != null ? fmtUsd.format(paperSession.pnl_total) : "—"}
            </p>
            <p className="mt-0.5 text-[10px] text-slate-500">
              Eq <span data-testid="paper-metric-equity">{paperSession?.equity != null ? fmtUsd.format(paperSession.equity) : "—"}</span> · Day{" "}
              <span data-testid="paper-metric-pnl-daily">{paperSession?.pnl_daily != null ? fmtUsd.format(paperSession.pnl_daily) : "—"}</span>
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Tape</p>
            <p className="mt-1 text-sm text-slate-300">{s.market_mode_label}</p>
            <p className="mt-0.5 text-[10px] text-slate-600">{s.execution_mode}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Mix</p>
            <p className="mt-1 text-xs tabular-nums text-slate-400">
              Fills <span data-testid="paper-metric-fills" className="text-emerald-200/90">{paperSession?.filled_trades ?? 0}</span>
              {" · "}
              Block <span data-testid="paper-metric-blocked" className="text-rose-200/90">{paperSession?.blocked ?? 0}</span>
              {" · "}
              Aside <span data-testid="paper-metric-skipped" className="text-cyan-200/85">{paperSession?.skipped ?? 0}</span>
              {" · "}
              Trim <span data-testid="paper-metric-reduced" className="text-amber-200/90">{paperSession?.reduced ?? 0}</span>
            </p>
            <p className="mt-1 text-[10px] text-slate-600">
              Router: allow {rm?.risk_full_allow_count ?? 0} · reduce {rm?.risk_reduced_count ?? 0} · block {rm?.risk_block_count ?? 0}
            </p>
          </div>
        </div>
      </section>
    );
  }
  return (
    <section
      id={sectionId}
      className={`${surfaceClass("")} scroll-mt-24 overflow-hidden ${emphasize ? "ring-1 ring-teal-500/25" : ""}`}
      aria-labelledby="autonomous-heading"
    >
      <div className="border-b border-white/[0.04] px-8 py-6">
        <p id="autonomous-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          {variant === "readonly" ? "Bot status (read-only)" : "Autonomous mode"}
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">
          {variant === "readonly" ? "Autonomous loop" : "Live autonomous paper loop"}
        </h2>
        <p className="mt-2 max-w-2xl text-xs text-slate-600">
          {variant === "readonly"
            ? "Stats only in Market Watch — switch to Live Paper Trading to start or stop the timed loop."
            : "Real-time clock: when ON, the loop pulls the latest tape on a timer and runs the same safety checks as manual runs. Fills stay simulated."}
        </p>
      </div>
      <div className="grid gap-6 border-b border-white/[0.04] px-8 py-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-black/25 px-4 py-3 ring-1 ring-white/[0.05]">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Bot state</p>
          <p className={`mt-2 text-lg font-semibold ${alive ? "text-emerald-200" : "text-slate-400"}`}>{alive ? "Running" : "Idle"}</p>
          <p className="mt-1 text-[11px] text-slate-500">{alive ? `Every ${auto.cadence_seconds}s while the system is running` : "Start below to wake the loop"}</p>
        </div>
        <div className="rounded-xl bg-black/25 px-4 py-3 ring-1 ring-white/[0.05]">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Cycles</p>
          <p className="mt-2 font-mono text-xs text-slate-400">
            Last:{" "}
            <span data-testid="autonomous-last-cycle-at">
              {auto.last_cycle_at ? formatOperatorTimestamp(auto.last_cycle_at, timeDisplay) : "—"}
            </span>
          </p>
          <p className="mt-1 font-mono text-xs text-teal-200/90">
            Next:{" "}
            <span data-testid="autonomous-next-cycle-at">
              {auto.next_cycle_at ? formatOperatorTimestamp(auto.next_cycle_at, timeDisplay) : "—"}
              {alive && auto.next_cycle_in_seconds != null ? ` · in ${auto.next_cycle_in_seconds}s` : ""}
            </span>
          </p>
        </div>
        <div className="rounded-xl bg-black/25 px-4 py-3 ring-1 ring-white/[0.05]">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Session PnL (paper)</p>
          <p data-testid="paper-metric-pnl-total" className="mt-2 text-lg font-semibold tabular-nums text-white">
            {paperSession?.pnl_total != null ? fmtUsd.format(paperSession.pnl_total) : "—"}
          </p>
          <p className="mt-1 text-[11px] text-slate-500">
            Equity{" "}
            <span data-testid="paper-metric-equity">
              {paperSession?.equity != null ? fmtUsd.format(paperSession.equity) : "—"}
            </span>{" "}
            · Day{" "}
            <span data-testid="paper-metric-pnl-daily">
              {paperSession?.pnl_daily != null ? fmtUsd.format(paperSession.pnl_daily) : "—"}
            </span>
          </p>
        </div>
        <div className="rounded-xl bg-black/25 px-4 py-3 ring-1 ring-white/[0.05]">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Trades · safety mix</p>
          <p className="mt-2 text-sm tabular-nums text-slate-300">
            Fills{" "}
            <span data-testid="paper-metric-fills" className="text-emerald-200/90">
              {paperSession?.filled_trades ?? 0}
            </span>
            {" · "}
            Blocked{" "}
            <span data-testid="paper-metric-blocked" className="text-rose-200/90">
              {paperSession?.blocked ?? 0}
            </span>
            {" · "}
            Stood aside{" "}
            <span data-testid="paper-metric-skipped" className="text-cyan-200/85">
              {paperSession?.skipped ?? 0}
            </span>
            {" · "}
            Trimmed{" "}
            <span data-testid="paper-metric-reduced" className="text-amber-200/90">
              {paperSession?.reduced ?? 0}
            </span>
          </p>
          <p className="mt-1 text-[11px] text-slate-500">
            Router (all paths): allow {rm?.risk_full_allow_count ?? 0} · reduce {rm?.risk_reduced_count ?? 0} · block{" "}
            {rm?.risk_block_count ?? 0} · stand-aside {rm?.risk_skip_count ?? 0}
          </p>
        </div>
      </div>
      <div className={`grid gap-6 px-8 py-6 ${variant === "full" ? "lg:grid-cols-[1.4fr_1fr]" : ""}`}>
        <div className="space-y-3 text-sm text-slate-500">
          <p>
            Market source: <span className="text-slate-300">{s?.market_mode_label ?? "—"}</span> · Execution:{" "}
            <span className="text-slate-300">{s?.execution_mode ?? "—"}</span>
          </p>
          <p className="text-xs text-slate-600">
            Review queue (paper):{" "}
            <span data-testid="paper-metric-review" className="text-slate-400">
              {paperSession?.review ?? 0}
            </span>{" "}
            escalations logged on intents.
          </p>
        </div>
        {variant === "full" ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              data-testid="autonomous-start-15"
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-40"
              disabled={!!busy}
              onClick={() => onAction("auto-start-15", "/control/autonomous/start?cadence_seconds=15")}
            >
              Start 15s
            </button>
            <button
              type="button"
              data-testid="autonomous-start-30"
              className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:opacity-40"
              disabled={!!busy}
              onClick={() => onAction("auto-start-30", "/control/autonomous/start?cadence_seconds=30")}
            >
              Start 30s
            </button>
            <button
              type="button"
              data-testid="autonomous-stop"
              className="rounded-lg px-4 py-2 text-sm font-semibold text-rose-300 transition hover:bg-rose-500/10 hover:text-rose-200 disabled:opacity-40"
              disabled={!!busy}
              onClick={() => onAction("auto-stop", "/control/autonomous/stop")}
            >
              Stop autonomous
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function PlainStoryPanel({ overview, chartContext }: { overview: Overview | null; chartContext: MarketChartContext | null }) {
  if (!overview) return null;
  return (
    <section className={`${surfaceClass("")} overflow-hidden`} aria-labelledby="plain-story-heading">
      <div className="border-b border-white/[0.04] px-8 py-6">
        <p id="plain-story-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Why the bot did this
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">Same run, in plain English</h2>
        <p className="mt-2 max-w-2xl text-xs text-slate-600">
          Matches the latest cycle: what the chart context showed, what the desk proposed, what risk allowed or blocked, and what the ledger recorded. No trading jargon required.
        </p>
      </div>
      <div className="space-y-4 bg-gradient-to-b from-teal-500/[0.06] to-transparent px-8 py-6">
        <ol className="list-none space-y-4">
          {simpleBotStoryLines(overview, chartContext).map((row) => (
            <li key={row.title} className="rounded-xl bg-black/20 px-4 py-3 ring-1 ring-white/[0.05]">
              <p className="text-xs font-semibold text-teal-200/90">{row.title}</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{row.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function LiveTapeChartPanel({
  chartPack,
  chartInterval,
  onChartInterval,
  timeDisplay,
  onTimeDisplayChange,
  positionNotional,
  sourceLabel,
  emphasize,
  sectionId,
  layout = "default",
}: {
  chartPack: MarketChartPack | null;
  chartInterval: ChartIntervalId;
  onChartInterval: (iv: ChartIntervalId) => void;
  timeDisplay: TimeDisplayMode;
  onTimeDisplayChange: (mode: TimeDisplayMode) => void;
  positionNotional: number | undefined;
  sourceLabel?: string;
  emphasize: boolean;
  sectionId?: string | undefined;
  layout?: "default" | "hero" | "workstation";
}) {
  const ctx = chartPack?.context ?? null;
  const chartHint = ctx?.source ? tapeSourceLabel(String(ctx.source)) : sourceLabel;
  const dataInterval = coerceChartInterval(chartPack?.interval, chartInterval);
  const intervalWords = chartIntervalLabel(dataInterval);
  const sourceClause =
    chartHint || sourceLabel
      ? `${intervalWords} OHLC · ${chartHint ?? sourceLabel}`
      : `${intervalWords} OHLC`;
  const workstation = layout === "workstation";
  return (
    <section
      {...(sectionId ? { id: sectionId } : {})}
      className={`${surfaceClass("")} scroll-mt-24 overflow-hidden ${emphasize ? "ring-1 ring-teal-500/25" : ""} ${workstation ? "flex min-h-0 flex-col lg:min-h-[32rem]" : ""}`}
      aria-labelledby="live-tape-heading"
    >
      <div className={`border-b border-white/[0.04] px-5 sm:px-8 ${layout === "hero" ? "py-4" : workstation ? "py-4" : "py-6"}`}>
        <p id="live-tape-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Live market chart
        </p>
        <h2 className={`mt-1.5 font-semibold text-white ${layout === "hero" || workstation ? "text-lg sm:text-xl" : "text-xl"}`}>
          {workstation
            ? `${chartPack?.symbol ? String(chartPack.symbol).replace("USD", "/USD") : "Market"} · ${sourceClause}`
            : layout === "hero"
              ? "Tape · markers · timeframes"
              : "Price chart · timeframes · markers"}
        </h2>
        {!workstation ? (
          <>
            <p className={`mt-2 max-w-2xl text-slate-600 ${layout === "hero" ? "text-[11px] leading-snug" : "text-xs"}`}>
              {chartPack?.symbol ? `${String(chartPack.symbol).replace("USD", "/USD")} — ` : null}
              {chartHint || sourceLabel
                ? `Data: ${intervalWords} OHLC from ${chartHint ?? sourceLabel}.`
                : `Data: ${intervalWords} OHLC (source label loading).`}{" "}
              Pan and zoom with OHLC readouts; markers snap to the bar when a decision was recorded (buy, sell, block, trim, review).
              Paper-only — this chart does not send orders to a venue.
            </p>
            {ctx?.what_the_bot_saw?.length ? (
              <ul className="mt-4 max-w-3xl list-disc space-y-1 pl-5 text-xs leading-relaxed text-slate-500">
                {ctx.what_the_bot_saw.map((line, i) => (
                  <li key={`${i}-${line.slice(0, 48)}`}>{line}</li>
                ))}
                {ctx.trade_hint ? <li className="text-slate-400">{ctx.trade_hint}</li> : null}
              </ul>
            ) : null}
          </>
        ) : (
          <p className="mt-2 max-w-3xl text-[11px] leading-snug text-slate-500">
            Markers = desk decisions on that bar. Paper-only — no venue orders from this surface.
            {ctx?.trade_hint ? <span className="mt-1 block text-slate-400">{ctx.trade_hint}</span> : null}
          </p>
        )}
      </div>
      <div className={`flex min-h-0 flex-1 flex-col px-5 pb-5 pt-4 sm:px-8 sm:pb-6 sm:pt-5 ${workstation ? "lg:flex-1" : ""}`}>
        <LiveCandleChart
          symbol={chartPack?.symbol ?? "BTCUSD"}
          candles={chartPack?.candles ?? []}
          markers={chartPack?.markers ?? []}
          positionNotional={positionNotional}
          sourceHint={chartHint}
          maShort={ctx?.ma_short ?? null}
          maLong={ctx?.ma_long ?? null}
          interval={chartInterval}
          timeDisplay={timeDisplay}
          onIntervalChange={onChartInterval}
          onTimeDisplayChange={onTimeDisplayChange}
          density={workstation ? "workstation" : "default"}
        />
      </div>
    </section>
  );
}

function PaperSessionSummaryPanel({ paper }: { paper: PaperSession | null }) {
  if (!paper) return null;
  return (
    <section className={`${surfaceClass("")} overflow-hidden`} aria-labelledby="session-summary-heading">
      <div className="border-b border-white/[0.04] px-8 py-6">
        <p id="session-summary-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Long-run paper session
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">Session summary</h2>
        <p className="mt-2 max-w-2xl text-xs text-slate-600">
          Totals across this database — useful when you leave autonomous mode on or run many lane cycles. Still simulated money only.
        </p>
      </div>
      <div className="grid gap-4 px-8 py-6 lg:grid-cols-3">
        <div className="rounded-xl bg-black/25 p-4 ring-1 ring-white/[0.06] lg:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">Behavior</p>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">{paper.session_story}</p>
        </div>
        <div className="space-y-3 rounded-xl bg-black/25 p-4 ring-1 ring-white/[0.06] text-xs text-slate-500">
          <p>
            <span className="text-slate-600">Straight allows · </span>
            <span className="font-mono text-slate-300">{paper.allow_full}</span>
          </p>
          {paper.best_win_label ? (
            <p>
              <span className="text-emerald-600/90">Highlight · </span>
              {paper.best_win_label}
            </p>
          ) : null}
          {paper.worst_loss_label ? (
            <p>
              <span className="text-rose-600/90">Rough edge · </span>
              {paper.worst_loss_label}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function WhyTradePanel({ overview }: { overview: Overview | null }) {
  const sig = overview?.latest_signal;
  const risk = overview?.latest_risk;
  const intent = overview?.latest_intent;
  const ex = overview?.latest_execution;
  const market = overview?.market_snapshot;
  if (!sig && !risk && !intent && !ex) return null;
  const verdict = str(risk?.verdict) ?? "—";
  const proposed = str(sig?.signal_type) ?? "—";
  const asset = str(sig?.asset) ?? str(intent?.asset) ?? "—";
  const conf = num(sig?.confidence);
  const requested = num(intent?.requested_size);
  const approved = num(intent?.approved_size);
  const reduced = requested != null && approved != null && approved < requested;
  const laneId = str(intent?.lane_id);
  const laneLabel = str(intent?.lane_label);
  const mType = str(intent?.market_type);
  const isFuturesLane = laneId === "futures_tactical" || mType === "futures_paper";
  const isSpotLane = laneId === "spot_momentum" || mType === "spot";
  const laneIntro = laneLabel
    ? `${laneLabel} — ${isFuturesLane ? "tactical futures lane (tighter caps, simulated)" : isSpotLane ? "spot momentum lane (steadier cadence, simulated)" : "governed lane (simulated)"}`
    : "Core pipeline — single-loop MA-style path (simulated fills)";
  const riskReasonsLower = (str(risk?.reasons) ?? "").toLowerCase();

  const whyEntered =
    isFuturesLane && sig
      ? `The tactical futures lane only moves when short-term bias and conviction clear a higher bar. It proposed ${proposed} on ${asset}${conf != null ? ` (~${Math.round(conf * 100)}% confidence)` : ""} — sizing stays small by design.`
      : isSpotLane && sig
        ? `The spot momentum lane looks for smoother trend continuation and fewer whipsaws. It proposed ${proposed} on ${asset}${conf != null ? ` (~${Math.round(conf * 100)}% confidence)` : ""} — paced for a steadier spot book.`
        : sig
          ? `The strategy proposed ${proposed} on ${asset}${conf != null ? ` at about ${Math.round(conf * 100)}% confidence` : ""}.`
          : "—";

  const whyRiskPlain =
    verdict === "skip"
      ? isFuturesLane
        ? "Plain view: futures lane stood aside — no tactical entry this cycle. Passive no-trade, not a hard safety block."
        : isSpotLane
          ? "Plain view: spot lane stood aside this cycle — chop, weak alignment, or lane hold; different from a block verdict."
          : "Plain view: stood aside — no entry this cycle. Use block counts only for true safety stops."
      : verdict === "block"
      ? riskReasonsLower.includes("duplicate_action")
        ? "Plain view: duplicate guard — a very similar idea was handled recently, so the desk stood down on purpose to avoid repeating the same action. The technical line still lists the policy code."
        : isFuturesLane
          ? "Plain view: futures lane said no — the playbook is strict, so bad tape, limits, or gates stop before an intent is committed."
          : isSpotLane
            ? "Plain view: spot lane said no — stale prices, volatility, or safety rails blocked before commitment."
            : "Plain view: the risk router blocked before a committed intent — tape, limits, or operator gates."
      : verdict === "escalate_for_review"
        ? isFuturesLane
          ? "Plain view: futures gate wants a human read — conviction or policy did not clear for an unsupervised simulated fill."
          : isSpotLane
            ? "Plain view: spot lane is holding — confidence or policy did not clear for an automatic simulated fill."
            : "Plain view: sent to review — not enough clearance for an unsupervised paper fill."
        : verdict === "allow_with_reduction"
          ? riskReasonsLower.includes("reduced_to_open_position")
            ? "Plain view: sell size matched the simulated long on the books — trims exposure instead of colliding with the global cap as if it were a fresh buy."
            : riskReasonsLower.includes("lane_soft_conviction_trim")
              ? "Plain view: futures lane had middling conviction — it took a bounded tactical clip instead of burning another review cycle."
              : isFuturesLane
                ? "Plain view: futures lane approved a smaller tactical size so exposure stays inside tight caps."
                : isSpotLane
                  ? "Plain view: spot lane approved a trimmed size so headroom and lane policy stay intact."
                  : "Plain view: approved but trimmed — exposure must stay inside policy."
          : verdict === "allow"
            ? "Plain view: cleared under current policy — fills stay simulated; no live orders."
            : `Plain view: risk state is ${verdict}.`;

  const volFlag = market && typeof market === "object" && market.volatility_flag === true;
  const whatMarketPlain =
    market && typeof market === "object"
      ? isFuturesLane
        ? `What the tape showed (futures context): ${str(market.symbol) ?? asset} around ${num(market.price)?.toLocaleString() ?? "—"} from ${tapeSourceLabel(str(market.source))}. ${
            volFlag ? "Volatility was flagged elevated — the tactical lane treats that as a serious brake." : "Volatility was calm — tactical lane still applies tight size and gates."
          }`
        : isSpotLane
          ? `What the tape showed (spot context): ${str(market.symbol) ?? asset} around ${num(market.price)?.toLocaleString() ?? "—"} from ${tapeSourceLabel(str(market.source))}. ${
            volFlag ? "Volatility was elevated — the spot lane may still pass or block depending on freshness and churn rules." : "Volatility was calm — spot lane favors steady continuation when other gates agree."
          }`
          : `Latest snapshot: ${str(market.symbol) ?? asset} last ${num(market.price)?.toLocaleString() ?? "—"} (${tapeSourceLabel(str(market.source))}${
              volFlag ? ", volatility elevated" : ", calm tape"
            }).`
      : "Ingest a market snapshot (seed or lane run) to see what the tape looked like at decision time.";

  const whyExitPlain =
    ex?.status === "filled"
      ? isFuturesLane
        ? "Execution (paper): tactical lane recorded a simulated fill at the reference price — no Kraken orders; this is evidence for the futures-style path only."
        : isSpotLane
          ? "Execution (paper): spot lane recorded a simulated fill at the snapshot price — no live venue; this matches the steadier spot narrative."
          : "Execution (paper): simulated fill at the reference price — no live venue orders; exit is immediate in this simulator."
      : ex?.status === "rejected"
        ? "Execution (paper): rejected in simulation (e.g. zero size) — book unchanged."
        : "No execution row yet, or still pending.";

  const sessionOutcomePlain =
    verdict === "skip"
      ? "Outcome: stand-aside cycle — ledger records skip, not a red-light block."
      : verdict === "block"
      ? riskReasonsLower.includes("duplicate_action")
        ? "Outcome: no trade — duplicate suppression fired; ledger still shows a normal block for audit."
        : isFuturesLane
          ? "Outcome: no tactical futures trade — safety won; artifact trail still records the stop."
          : isSpotLane
            ? "Outcome: no spot trade — lane stayed defensive; proof trail shows the halt."
            : "Outcome: no trade — safety stopped the path."
      : verdict === "escalate_for_review"
        ? "Outcome: queued for review — no autonomous simulated fill."
        : ex?.status === "filled"
          ? "Outcome: governed paper fill on record — artifacts and performance reflect this path."
          : "Outcome: check execution status in the pipeline below.";

  return (
    <section className={`${surfaceClass("")} overflow-hidden`} aria-labelledby="why-trade-heading">
      <div className="border-b border-white/[0.04] px-8 py-6">
        <p id="why-trade-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Why this trade?
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">What happened this cycle</h2>
        <p className="mt-1 text-xs text-slate-600">
          Same order as the pipeline: signal → risk → signed plan → execution (simulated). Plain view first; technical line below.
        </p>
      </div>
      <div className="space-y-4 px-8 py-6 text-sm leading-relaxed text-slate-500">
        <p>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Lane</span>
          <br />
          <span className="text-slate-200">{laneIntro}</span>
        </p>
        <p>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Why enter</span>
          <br />
          {whyEntered}
        </p>
        <p>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">What the market showed</span>
          <br />
          {whatMarketPlain}
        </p>
        <p>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Why blocked, reduced, or reviewed</span>
          <br />
          {whyRiskPlain}
        </p>
        <p className="rounded-lg bg-black/20 px-3 py-2 text-xs text-slate-600 ring-1 ring-white/[0.04]">
          <span className="font-semibold text-slate-500">Technical</span>
          {" · "}
          <span className={riskValueClass(verdict)}>{verdict}</span>
          {risk?.reasons ? (
            <>
              {" · "}
              <span className="font-mono text-[11px] text-slate-500" title="Verbatim policy payload from the risk artifact">
                {str(risk.reasons)}
              </span>
            </>
          ) : null}
        </p>
        <p>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Size</span>
          <br />
          {reduced
            ? `Requested ${fmtUsd.format(requested!)} but reduced to ${fmtUsd.format(approved!)} under policy / lane headroom.`
            : approved != null
              ? `Approved notional ${fmtUsd.format(approved)}.`
              : verdict === "skip"
              ? "No signed intent — stood aside (no action)."
              : "No approved size — blocked or under review."}
        </p>
        <p>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Why exit / execution</span>
          <br />
          {whyExitPlain}
        </p>
        <p>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Session outcome</span>
          <br />
          {sessionOutcomePlain}
        </p>
      </div>
    </section>
  );
}

function CycleHistoryPanel({ overview, timeDisplay }: { overview: Overview | null; timeDisplay: TimeDisplayMode }) {
  const rows = overview?.cycle_history ?? [];
  const tone = (o: string) =>
    o === "allowed"
      ? "text-emerald-200"
      : o === "reduced"
        ? "text-sky-200"
        : o === "blocked"
          ? "text-rose-200"
          : o === "skipped"
            ? "text-cyan-200"
            : o === "review"
              ? "text-violet-200"
              : "text-slate-300";
  const laneBadgeClass = (laneId: string | null | undefined) => {
    if (laneId === "futures_tactical") return "bg-amber-500/15 text-amber-200/90 ring-amber-500/25";
    if (laneId === "spot_momentum") return "bg-teal-500/15 text-teal-200/90 ring-teal-500/25";
    if (laneId) return "bg-white/[0.06] text-slate-400 ring-white/10";
    return "bg-slate-500/15 text-slate-400 ring-slate-500/20";
  };
  return (
    <section className={`${surfaceClass("")} overflow-hidden`} aria-labelledby="cycle-history-heading">
      <div className="border-b border-white/[0.04] px-8 py-6">
        <p id="cycle-history-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Autonomous cycle history
        </p>
        <p className="mt-2 max-w-3xl text-xs text-slate-600">
          One card per autonomous run: plain-language summary first, then a compact technical line. Spot and futures lanes use different wording on purpose.
        </p>
        <p data-testid="cycle-history-count" className="mt-2 font-mono text-xs text-slate-500">
          Recorded cycles (this session): {rows.length}
        </p>
      </div>
      <div className="px-8 py-6">
        {rows.length === 0 ? (
          <p className="text-sm text-slate-600">No autonomous cycles yet — start 15s or 30s mode.</p>
        ) : (
          <div className="space-y-3">
            {rows.map((r, idx) => (
              <div key={`${r.timestamp}-${idx}`} className="rounded-lg bg-white/[0.03] px-4 py-3 ring-1 ring-white/[0.05]">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className={`text-sm font-semibold uppercase ${tone(r.outcome)}`}>{r.outcome}</span>
                  {r.lane_label || r.lane_id ? (
                    <span
                      className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ring-1 ${laneBadgeClass(r.lane_id)}`}
                    >
                      {r.lane_id === "futures_tactical" ? "Futures" : r.lane_id === "spot_momentum" ? "Spot" : r.lane_label ?? r.lane_id}
                    </span>
                  ) : (
                    <span className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ring-1 ${laneBadgeClass(null)}`}>
                      Core pipeline
                    </span>
                  )}
                  <span
                    data-testid={idx === 0 ? "cycle-history-latest-ts" : undefined}
                    className="font-mono text-[11px] text-slate-600"
                  >
                    {formatOperatorTimestamp(r.timestamp, timeDisplay)}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-500">{r.note}</p>
                {r.detail ? <p className="mt-2 text-sm leading-relaxed text-slate-300">{r.detail}</p> : null}
                {r.detail_technical ? (
                  <p className="mt-2 font-mono text-[10px] text-slate-600">
                    <span className="text-slate-500">Technical · </span>
                    {r.detail_technical}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function QuickStartStrip({
  overview,
  traceLen,
}: {
  overview: Overview | null;
  traceLen: number;
}) {
  const active = quickStartActiveStep(overview);
  const hasSignal = overview?.latest_signal != null;
  const hasExec = overview?.latest_execution != null;

  const steps = [
    {
      n: 1,
      title: "Load demo data",
      body: "Seeds a sample portfolio and tape so the rest of the console has something real to attach to.",
      done: hasSignal,
    },
    {
      n: 2,
      title: "Run one cycle",
      body: "Idea → safety check → signed plan → simulated fill, in one pass.",
      done: hasExec,
    },
    {
      n: 3,
      title: "Read the proof trail",
      body: "Scroll to the trail: each step leaves a row you can match to the pipeline above.",
      done: hasExec && traceLen > 0,
    },
    {
      n: 4,
      title: "Try safety controls (optional)",
      body: "Pause, step, or risk pause to see how you can stop the loop without losing context.",
      done: false,
    },
  ];

  return (
    <section className={`${surfaceClass("")} overflow-hidden`} aria-labelledby="quickstart-heading">
      <div className="border-b border-white/[0.04] px-8 py-7">
        <p id="quickstart-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Quick start
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">Four steps to learn the console</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-500">
          VeriTrade runs ideas through safety checks, locks a signed plan, then records a simulated fill. This build never sends live orders;
          you still see Kraken-shaped routing and an agent identity hook so you know how production would be wired.
        </p>
      </div>
      <ol className="grid gap-4 px-6 py-8 sm:grid-cols-2 lg:grid-cols-4 lg:px-8">
        {steps.map((s, i) => {
          const isActive = active === i;
          return (
            <li
              key={s.n}
              className={`rounded-xl px-5 py-5 transition ${isActive ? "bg-teal-500/[0.08] ring-1 ring-teal-500/25" : "bg-white/[0.02] ring-1 ring-white/[0.04]"}`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${
                    s.done ? "bg-emerald-500/20 text-emerald-200" : isActive ? "bg-teal-500/20 text-teal-100" : "bg-white/[0.05] text-slate-500"
                  }`}
                >
                  {s.done ? "✓" : s.n}
                </span>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Step {s.n}</span>
              </div>
              <p className="mt-3 font-medium text-white">{s.title}</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{s.body}</p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function GuidedActionButton({
  action,
  busy,
  variant,
  onPost,
}: {
  action: GuidanceAction;
  busy: string | null;
  variant: "primary" | "secondary";
  onPost: (label: string, path: string) => void;
}) {
  const primaryCls =
    "rounded-lg bg-teal-500 px-6 py-3 text-sm font-semibold text-slate-950 shadow-[0_0_24px_-8px_rgba(45,212,191,0.65)] transition hover:bg-teal-400 disabled:opacity-40";
  const secondaryCls =
    "rounded-lg px-4 py-3 text-sm font-medium text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-300 disabled:opacity-40";
  const cls = variant === "primary" ? primaryCls : secondaryCls;
  if (action.type === "post") {
    return (
      <button type="button" disabled={!!busy} className={cls} onClick={() => onPost(action.label, action.path)}>
        {action.label}
      </button>
    );
  }
  return (
    <button type="button" disabled={!!busy} className={cls} onClick={() => scrollToId(action.targetId)}>
      {action.label}
    </button>
  );
}

function GuidedNextPanel({
  guidance,
  busy,
  onPost,
}: {
  guidance: Guidance;
  busy: string | null;
  onPost: (label: string, path: string) => void;
}) {
  return (
    <section className={`${surfaceClass("")} overflow-hidden ring-1 ring-teal-500/15`} aria-labelledby="guided-heading">
      <div className="px-8 py-7">
        <p id="guided-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Guided Proof Demo
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">What should I do next?</h2>
        <p className="mt-3 text-lg font-medium leading-snug text-slate-200">{guidance.headline}</p>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500">{guidance.body}</p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          {guidance.primary ? <GuidedActionButton action={guidance.primary} busy={busy} variant="primary" onPost={onPost} /> : null}
          {guidance.secondary ? <GuidedActionButton action={guidance.secondary} busy={busy} variant="secondary" onPost={onPost} /> : null}
        </div>
      </div>
    </section>
  );
}

function stateLabel(visual: PipelineVisualState): string {
  if (visual === "waiting") return "Waiting";
  if (visual === "complete") return "Complete";
  if (visual === "blocked") return "Blocked";
  return "Review";
}

function stateStyles(visual: PipelineVisualState): string {
  if (visual === "complete") return "bg-emerald-500/15 text-emerald-200 ring-emerald-500/30";
  if (visual === "blocked") return "bg-rose-500/15 text-rose-200 ring-rose-500/30";
  if (visual === "attention") return "bg-violet-500/15 text-violet-200 ring-violet-500/30";
  return "bg-slate-800/80 text-slate-400 ring-white/10";
}

function ChallengeStrip({ challenge }: { challenge: ChallengeContext | undefined }) {
  const [open, setOpen] = useState(false);
  if (!challenge) return null;
  const ks = challenge.kraken_surface;
  const draftJson = ks.latest_order_draft ? JSON.stringify(ks.latest_order_draft, null, 2) : null;

  return (
    <section className={`${surfaceClass("overflow-hidden")}`} aria-labelledby="system-status-heading">
      <div className="px-8 py-7">
        <p id="system-status-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          System status
          <Tip text="Agent identity, policy version, validation tags, and how a live venue would connect — fills here stay simulated unless you arm live routing elsewhere." />
        </p>
        <div className="mt-4 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1 space-y-4">
            <p className="text-sm leading-relaxed text-slate-400">
              <span className="font-mono text-[11px] text-slate-600">
                Agent identity
                <Tip text="Who is acting — ERC-8004 draft-aligned surfaces; optional URI stub for a future on-chain agentURI." />
              </span>{" "}
              <span className="break-all text-slate-200">{challenge.agent_id}</span>
              <span className="mx-2 text-slate-700">·</span>
              <span className="text-slate-600">Rules version</span>{" "}
              <span className="text-slate-100">{challenge.policy_version}</span>
            </p>
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                Validation artifacts
                <Tip text="Each label matches something you can point to in the UI or API—proof the system is end-to-end auditable." />
              </p>
              <div className="flex flex-wrap gap-2">
                {challenge.trust_signals.map((t) => (
                  <span key={t} className="rounded-md bg-white/[0.04] px-2.5 py-1 font-mono text-[10px] text-slate-500">
                    {t}
                  </span>
                ))}
              </div>
            </div>
            <p className="text-sm text-slate-500">
              <span className="text-slate-400">
                Kraken execution surface
                <Tip text="Shows how a live venue would be wired — CLI stub and gates. Fills stay simulated unless you explicitly enable more." />
              </span>{" "}
              — routing {ks.routing_mode}, provider {ks.active_execution_provider}. Gates: Kraken flag {String(ks.kraken_execution_enabled_flag)},
              real orders {String(ks.allow_real_orders)}.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className="shrink-0 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-300"
          >
            {open ? "Hide" : "Identity & CLI"} · ERC-8004 · draft
          </button>
        </div>
        {open ? (
          <div className="mt-8 border-t border-white/[0.04] pt-8">
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-xl bg-black/20 p-5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">ERC-8004 URI stub (optional)</p>
                <p className="mt-3 break-all font-mono text-xs leading-relaxed text-slate-400">
                  {challenge.erc8004_agent_uri_stub || "— configure ERC8004_AGENT_URI_STUB"}
                </p>
                <p className="mt-5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Effective agentURI (demo)</p>
                <p className="mt-2 break-all font-mono text-[10px] leading-relaxed text-slate-500">
                  {challenge.erc8004_draft.agent_uri_effective || "—"}
                </p>
                <p className="mt-4 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Registration file</p>
                <p className="mt-2 break-all font-mono text-[10px] text-teal-500/90">
                  <a href={challenge.erc8004_draft.agent_registration_url} className="hover:underline" target="_blank" rel="noreferrer">
                    {challenge.erc8004_draft.agent_registration_url}
                  </a>
                </p>
                <p className="mt-2 break-all font-mono text-[10px] text-slate-500">
                  <a href={challenge.erc8004_draft.agent_registration_static_url} className="hover:underline" target="_blank" rel="noreferrer">
                    {challenge.erc8004_draft.agent_registration_static_url}
                  </a>
                </p>
                <p className="mt-3 text-[10px] text-slate-600">
                  Identity registry: {challenge.erc8004_draft.identity_registry}. On-chain validation attested:{" "}
                  {challenge.erc8004_draft.on_chain_validation_attested ? "yes" : "no"}.
                </p>
                <p className="mt-5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Intent commitment</p>
                <p className="mt-2 font-mono text-xs text-slate-500">{challenge.intent_commitment_algorithm}</p>
              </div>
              <div className="rounded-xl bg-black/20 p-5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">CLI stub</p>
                <p className="mt-3 font-mono text-xs text-slate-400">{ks.cli_command_stub}</p>
                {draftJson ? (
                  <pre className="mt-4 max-h-44 overflow-auto rounded-lg bg-black/40 p-4 font-mono text-[10px] leading-relaxed text-slate-500">
                    {draftJson}
                  </pre>
                ) : (
                  <p className="mt-4 text-sm text-slate-600">Run a cycle after seed to materialize a draft.</p>
                )}
                <p className="mt-3 text-xs text-slate-600">{ks.note}</p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function pipelineOutcomeReadout(overview: Overview | null): { headline: string; body: string } {
  if (!overview?.latest_risk) {
    return {
      headline: "Current pipeline ending",
      body: "Run a preset (or seed + run cycle) to lock in a known-good path: allow, block, or trimmed approval.",
    };
  }
  const v = str(overview.latest_risk.verdict) ?? "";
  const intent = overview.latest_intent;
  const ex = overview.latest_execution;
  const approved = num(intent?.approved_size);

  if (v === "block") {
    return {
      headline: "Ending: blocked at safety",
      body: "Risk stopped this idea before a trade plan or fill—expected when volatility or limits say no.",
    };
  }
  if (v === "escalate_for_review") {
    return {
      headline: "Ending: review queue",
      body: "Automatic routing paused for a human decision—no unsupervised fill in this path.",
    };
  }
  if (v === "allow_with_reduction") {
    return {
      headline: "Ending: approved with a smaller size",
      body:
        approved != null
          ? `Risk trimmed the request to ${fmtUsd.format(approved)} notional; intent commitment and paper fill follow that reduced size.`
          : "Risk trimmed size to fit policy; intent and paper execution use the reduced amount.",
    };
  }
  if (v === "allow") {
    const filled = str(ex?.status) === "filled";
    return {
      headline: filled ? "Ending: full approval → paper fill" : "Ending: approved — check execution",
      body: filled
        ? "Safety checks passed, a committed plan was recorded, and the paper ledger shows a fill."
        : "Safety checks passed and a committed plan exists—see execution status in the strip below.",
    };
  }
  if (v === "skip") {
    return {
      headline: "Ending: stood aside",
      body: "No committed trade plan this cycle — the router recorded stand-aside. Hard blocks show as block, not skip.",
    };
  }
  return {
    headline: `Ending: ${v}`,
    body: "Use the risk and execution tiles and the decision pipeline for detail.",
  };
}

function ScenarioPresetsBar({
  busy,
  onScenario,
  overview,
}: {
  busy: string | null;
  onScenario: (label: string, path: string) => void;
  overview: Overview | null;
}) {
  const chip =
    "rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-2.5 text-left text-sm font-medium text-slate-200 transition hover:border-teal-500/30 hover:bg-teal-500/[0.06] disabled:opacity-35";
  const readout = pipelineOutcomeReadout(overview);
  return (
    <section
      id="scenario-presets"
      className={`${surfaceClass("scroll-mt-28 overflow-hidden")} ring-1 ring-amber-400/10`}
      aria-labelledby="scenario-presets-heading"
    >
      <div className="border-b border-white/[0.04] px-8 py-6">
        <p id="scenario-presets-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Demo scenarios
          <Tip text="One tap resets data, injects a fixed market + signal, and runs the pipeline — three predictable endings for walkthroughs." />
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">Preset outcomes</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500">
          Safe → allowed trade · Volatile → blocked at risk · Oversized → reduced approval. Same engine, three clear endings—no random signal.
        </p>
      </div>
      <div className="grid gap-3 px-6 py-8 sm:grid-cols-3 sm:px-8">
        {SCENARIO_PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            disabled={!!busy}
            className={chip}
            title={p.hint}
            onClick={() => onScenario(`scenario:${p.id}`, `/demo/scenario/${p.id}`)}
          >
            <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-600">Run preset</span>
            <span className="mt-1 block text-sm font-semibold text-white">{p.label}</span>
            <span className="mt-2 block text-xs leading-relaxed text-slate-600">{p.hint}</span>
          </button>
        ))}
      </div>
      <div className="border-t border-white/[0.04] bg-white/[0.02] px-8 py-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">Plain-English result</p>
        <p data-testid="scenario-outcome-headline" className="mt-2 text-sm font-semibold text-teal-100/95">
          {readout.headline}
        </p>
        <p data-testid="scenario-outcome-body" className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-500">
          {readout.body}
        </p>
      </div>
    </section>
  );
}

function FitRow({ ok, label, hint }: { ok: boolean; label: string; hint: string }) {
  return (
    <div className="flex gap-3 rounded-lg bg-white/[0.02] px-3 py-2.5 ring-1 ring-white/[0.04]">
      <span
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
          ok ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/35" : "bg-slate-800 text-slate-600 ring-1 ring-white/10"
        }`}
        aria-hidden
      >
        {ok ? "✓" : "—"}
      </span>
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-200">{label}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-slate-600">{hint}</p>
      </div>
    </div>
  );
}

function AgentIdentityTrustPanel({ overview }: { overview: Overview | null }) {
  const c = overview?.challenge;
  const r = overview?.rubric_metrics;
  if (!c || !r) return null;
  return (
    <article className={`${surfaceClass("h-full overflow-hidden")}`} aria-labelledby="agent-trust-heading">
      <div className="border-b border-white/[0.04] px-6 py-5">
        <p id="agent-trust-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Agent identity &amp; trust
          <Tip text="ERC-8004 draft-aligned identity surfaces plus a simple score from artifacts and risk outcomes — quick read on whether the desk is behaving." />
        </p>
        <h3 className="mt-2 text-lg font-semibold text-white">Identity &amp; posture</h3>
      </div>
      <div className="space-y-4 px-6 py-6">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Agent ID</p>
          <p className="mt-1 break-all font-mono text-xs text-teal-200/90">{c.agent_id}</p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Agent URI stub</p>
          <p className="mt-1 break-all font-mono text-xs text-slate-500">{c.erc8004_agent_uri_stub || "— configure ERC8004_AGENT_URI_STUB"}</p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Commitment algorithm</p>
          <p className="mt-1 font-mono text-[11px] leading-relaxed text-slate-500">{c.intent_commitment_algorithm}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          <div className="rounded-lg bg-black/25 px-2 py-3 text-center ring-1 ring-white/[0.06]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Artifacts</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-white">{r.validation_artifact_count}</p>
          </div>
          <div className="rounded-lg bg-black/25 px-2 py-3 text-center ring-1 ring-white/[0.06]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Allowed</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-emerald-200/90">{r.risk_full_allow_count}</p>
          </div>
          <div className="rounded-lg bg-black/25 px-2 py-3 text-center ring-1 ring-white/[0.06]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Reduced</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-sky-200/90">{r.risk_reduced_count}</p>
          </div>
          <div className="rounded-lg bg-black/25 px-2 py-3 text-center ring-1 ring-white/[0.06]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Blocked</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-rose-200/90">{r.risk_block_count}</p>
          </div>
          <div className="rounded-lg bg-black/25 px-2 py-3 text-center ring-1 ring-white/[0.06]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Stood aside</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-cyan-200/90">{r.risk_skip_count ?? 0}</p>
          </div>
        </div>
        <div className="rounded-xl bg-gradient-to-br from-teal-500/[0.08] to-transparent px-4 py-4 ring-1 ring-teal-500/20">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Trust score (0–100)</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums text-teal-100">{r.trust_score_0_100}</p>
          <p className="mt-2 text-sm font-medium text-slate-300">{r.trust_posture_label}</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">{r.trust_score_explainer}</p>
        </div>
      </div>
    </article>
  );
}

function KrakenExecutionAdapterPanel({ overview }: { overview: Overview | null }) {
  const c = overview?.challenge;
  const ctrl = overview?.control;
  if (!c || !ctrl) return null;
  const ks = c.kraken_surface;
  const draft = ks.latest_order_draft;
  const draftLine = draft ? JSON.stringify(draft) : null;
  const gateOpen = ks.kraken_execution_enabled_flag && ks.allow_real_orders;
  const paperDefault = ctrl.trading_mode === "paper";
  return (
    <article className={`${surfaceClass("h-full overflow-hidden")}`} aria-labelledby="kraken-adapter-heading">
      <div className="border-b border-white/[0.04] px-6 py-5">
        <p id="kraken-adapter-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Kraken execution adapter
          <Tip text="Kraken-aligned: typed order draft and routing metadata. Simulator owns fills; live venue path stays gated in this build." />
        </p>
        <h3 className="mt-2 text-lg font-semibold text-white">Venue surface</h3>
      </div>
      <div className="space-y-4 px-6 py-6">
        <p className="text-sm leading-relaxed text-slate-500">
          <strong className="font-medium text-slate-400">Kraken-ready, safely gated:</strong> this console shows how a venue CLI would receive a
          structured order and policy context — default fills stay in-process and simulated unless you explicitly arm live routing elsewhere.
        </p>
        <div className="flex flex-wrap gap-2">
          <Badge label={ks.active_execution_provider} tone="sky" />
          <Badge label={ks.routing_mode.replace(/_/g, " ")} tone="indigo" />
          {paperDefault ? <Badge label="Paper default" tone="emerald" /> : <Badge label={`${ctrl.trading_mode} mode`} tone="slate" />}
          <Badge label={gateOpen ? "Live gate open" : "Live gate closed"} tone={gateOpen ? "amber" : "slate"} />
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Order draft (CLI-shaped)</p>
          <p className="mt-1 font-mono text-xs text-slate-500">{ks.cli_command_stub}</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            Mirrors what a Kraken CLI wrapper would consume; no outbound venue call in this demo build.
          </p>
        </div>
        {draftLine ? (
          <pre className="max-h-36 overflow-auto rounded-lg bg-black/35 p-3 font-mono text-[10px] leading-relaxed text-slate-500">{draftLine}</pre>
        ) : (
          <p className="text-sm text-slate-600">Run a preset or cycle to materialize a draft from the latest approved intent.</p>
        )}
        <p className="text-xs leading-relaxed text-slate-600">{ks.note}</p>
      </div>
    </article>
  );
}

function ChallengeFitPanel({ overview }: { overview: Overview | null }) {
  const f = overview?.challenge_fit;
  if (!f) return null;
  return (
    <article className={`${surfaceClass("h-full overflow-hidden")}`} aria-labelledby="challenge-fit-heading">
      <div className="border-b border-white/[0.04] px-6 py-5">
        <p id="challenge-fit-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Integration checklist
          <Tip text="Session-level checks: routing surface, identity hook, safe demo mode, risk router, and artifacts — all derived from live config and recent activity." />
        </p>
        <h3 className="mt-2 text-lg font-semibold text-white">What’s wired up</h3>
      </div>
      <div className="space-y-2 px-6 py-6">
        <FitRow
          ok={f.kraken_execution_surface_aligned}
          label="Kraken-aligned execution surface"
          hint="Typed CLI draft + routing metadata visible in-product."
        />
        <FitRow
          ok={f.erc8004_identity_hooks}
          label="ERC-8004 draft URI stub (optional on-chain pointer)"
          hint="Green when ERC8004_AGENT_URI_STUB is set — future agentURI after Identity Registry mint."
        />
        <FitRow
          ok={f.erc8004_agent_registration_available}
          label="ERC-8004 draft registration file exposed"
          hint="GET /challenge/agent-registration plus /.well-known/agent-registration.json (see docs/erc8004-alignment.md)."
        />
        <FitRow
          ok={f.combined_submission_story}
          label="End-to-end story in one console"
          hint="Venue path, identity hook, and validation trail surface together without jumping tools."
        />
        <FitRow ok={f.paper_safe_demo_mode} label="Paper-safe demo mode" hint="Default fills stay simulated; live orders gated off." />
        <FitRow ok={f.risk_router_active} label="Risk router active" hint="At least one risk verdict recorded this session." />
        <FitRow ok={f.validation_artifacts_active} label="Validation artifacts active" hint="Durable artifact rows exist for audit / replay." />
      </div>
    </article>
  );
}

function PipelineRail({ overview }: { overview: Overview | null }) {
  const stages = useMemo(() => {
    return PIPELINE_KINDS.map((kind) => ({
      kind,
      publicTitle: stagePublicTitle(kind),
      challengeSub: stageChallengeSubtitle(kind),
      visual: pipelineStageVisualState(kind, overview),
      technical: pipelineStageSummary(kind, overview),
      plainLine: pipelineStagePlainExplain(kind),
      happened: pipelineWhatHappenedPlain(kind, overview),
    }));
  }, [overview]);

  return (
    <section className={`${surfaceClass("relative overflow-hidden")} ring-1 ring-teal-500/[0.07]`} aria-labelledby="pipeline-heading">
      <div className="border-b border-white/[0.04] px-8 py-7">
        <p id="pipeline-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          How a trade becomes real (on paper)
          <Tip text="Tap a stage for the short story first; expand for the technical line when you need field names." />
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">Decision pipeline</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500">
          Four stops every autonomous run hits. Big type is plain English; small caps line is the technical stage name.
        </p>
      </div>

      {/* Connected rail — desktop */}
      <div className="relative hidden px-10 pb-2 pt-10 lg:block">
        <div
          className="absolute left-[12.5%] right-[12.5%] top-[2.25rem] h-[2px] rounded-full bg-gradient-to-r from-white/[0.06] via-teal-500/35 to-white/[0.06]"
          aria-hidden
        />
        <div className="relative flex justify-between">
          {stages.map((step, i) => {
            const done = step.visual === "complete" || step.visual === "attention";
            const blocked = step.visual === "blocked";
            return (
              <div key={step.kind} className="flex w-0 flex-1 justify-center">
                <div
                  className={`relative z-10 flex h-11 w-11 items-center justify-center rounded-full text-sm font-semibold tabular-nums transition ${
                    done
                      ? "bg-teal-500/20 text-teal-100 shadow-[0_0_24px_-4px_rgba(45,212,191,0.45)] ring-2 ring-teal-400/50"
                      : blocked
                        ? "bg-rose-500/15 text-rose-200 ring-2 ring-rose-400/35"
                        : "bg-[#0c1220] text-slate-500 ring-1 ring-white/[0.08]"
                  }`}
                  aria-label={`Stage ${i + 1} ${stateLabel(step.visual)}`}
                >
                  {done ? "✓" : blocked ? "!" : i + 1}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Interactive stages */}
      <div className="grid gap-4 px-6 pb-10 pt-6 sm:px-8 lg:grid-cols-2 lg:gap-5 xl:grid-cols-4">
        {stages.map((step, i) => {
          const active = step.visual === "complete" || step.visual === "attention";
          const blocked = step.visual === "blocked";
          return (
            <details
              key={step.kind}
              className="group rounded-xl bg-white/[0.02] ring-1 ring-white/[0.05] open:bg-white/[0.03] open:ring-teal-500/20"
            >
              <summary className="cursor-pointer list-none px-5 py-4 [&::-webkit-details-marker]:hidden">
                <div className="mb-3 flex items-center gap-3 lg:hidden">
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                      active
                        ? "bg-teal-500/20 text-teal-100 ring-2 ring-teal-400/40"
                        : blocked
                          ? "bg-rose-500/15 text-rose-200 ring-2 ring-rose-400/30"
                          : "bg-[#0c1220] text-slate-500 ring-1 ring-white/[0.08]"
                    }`}
                  >
                    {active ? "✓" : blocked ? "!" : i + 1}
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${stateStyles(step.visual)}`}>
                    {stateLabel(step.visual)}
                  </span>
                </div>
                <div className="hidden items-center justify-between gap-2 lg:flex">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${stateStyles(step.visual)}`}>
                    {stateLabel(step.visual)}
                  </span>
                  <span className="text-slate-600 transition group-open:text-teal-400/80">▼</span>
                </div>
                <p className="mt-1 text-base font-semibold text-white">{step.publicTitle}</p>
                <p className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-slate-600">{step.challengeSub}</p>
                <p className="mt-3 text-sm leading-relaxed text-slate-500">{step.happened}</p>
                <p className="mt-2 text-xs text-slate-600 lg:hidden">Tap for the full lesson + technical line</p>
                <p className="mt-2 hidden text-xs text-slate-600 lg:block">Click to expand details</p>
              </summary>
              <div className="space-y-4 border-t border-white/[0.04] px-5 pb-5 pt-4">
                <p className="text-sm leading-relaxed text-slate-400">{step.plainLine}</p>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Technical summary</p>
                  <p className="mt-1 font-mono text-xs leading-relaxed text-slate-500">{step.technical}</p>
                </div>
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}

function CommandSurface({
  busy,
  lastAction,
  err,
  onAction,
  onRefresh,
  hideDemoPresets,
  compact,
}: {
  busy: string | null;
  lastAction: string | null;
  err: string | null;
  onAction: (label: string, path: string) => void;
  onRefresh: () => void;
  /** Live Paper: presets live under “More tools” so the command bar stays minimal */
  hideDemoPresets?: boolean;
  compact?: boolean;
}) {
  const cmd =
    "rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-200 disabled:opacity-35";
  const cmdPrimary =
    "rounded-lg bg-teal-500 px-5 py-2 text-sm font-semibold text-slate-950 shadow-[0_0_20px_-6px_rgba(45,212,191,0.7)] transition hover:bg-teal-400 disabled:opacity-40";
  const cmdStop =
    "rounded-lg px-4 py-2 text-sm font-semibold text-rose-300/90 transition hover:bg-rose-500/10 hover:text-rose-200 disabled:opacity-35";

  return (
    <section id="command-bar" className="px-1 scroll-mt-28" aria-labelledby="command-heading">
      <p id="command-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
        {compact ? "Commands" : "Operations"}
      </p>
      {compact ? (
        <p className="mt-1 text-xs text-slate-600">
          Seed / run / risk pause / stop — same governed paths as always.
          <Tip text="Seed + Run cycle is the fastest way to populate the pipeline and proof trail. Risk pause is an operator kill-switch — clears when you say so." />
        </p>
      ) : (
        <>
          <h2 className="mt-2 text-xl font-semibold text-white">
            Command bar
            <Tip text="Seed + Run cycle is the fastest way to populate the pipeline and proof trail. Risk pause is an operator kill-switch — clears when you say so." />
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
            One bright button runs the main loop; everything else stays quiet. Stop is the only destructive action.
          </p>
        </>
      )}

      <div className={`flex flex-col gap-4 rounded-xl bg-white/[0.02] py-3 pl-4 pr-3 ring-1 ring-white/[0.04] sm:flex-row sm:flex-wrap sm:items-center sm:gap-2 sm:py-2.5 ${compact ? "mt-3" : "mt-6"}`}>
        <div className="flex flex-col gap-3 border-b border-white/[0.04] pb-3 sm:border-0 sm:pb-0">
          <div className="flex flex-wrap items-center gap-1">
            <span className="mr-2 hidden text-[10px] font-semibold uppercase tracking-wider text-slate-700 sm:inline">Demo</span>
            <button type="button" className={cmd} disabled={!!busy} onClick={() => onAction("seed", "/demo/seed")}>
              Seed
            </button>
            <button type="button" className={cmdPrimary} disabled={!!busy} onClick={() => onAction("run", "/demo/run-once")}>
              Run cycle
            </button>
          </div>
          {hideDemoPresets ? null : (
            <div className="flex flex-wrap items-center gap-1">
              <span className="mr-2 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Presets</span>
              {SCENARIO_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  title={p.hint}
                  className={cmd}
                  disabled={!!busy}
                  onClick={() => onAction(`scenario:${p.id}`, `/demo/scenario/${p.id}`)}
                >
                  {p.id === "safe_allow" ? "Safe" : p.id === "volatile_block" ? "Volatile" : "Oversized"}
                </button>
              ))}
            </div>
          )}
        </div>

        <span className="hidden h-7 w-px shrink-0 bg-white/[0.06] sm:block" aria-hidden />

        <div className="flex flex-wrap items-center gap-1">
          <span className="mr-2 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Control</span>
          <button type="button" className={cmd} disabled={!!busy} onClick={() => onAction("step", "/control/step")}>
            Step
          </button>
          <button type="button" className={cmd} disabled={!!busy} onClick={() => onAction("pause", "/control/pause")}>
            Pause
          </button>
          <button type="button" className={cmd} disabled={!!busy} onClick={() => onAction("start", "/control/start")}>
            Start
          </button>
        </div>

        <span className="hidden h-7 w-px shrink-0 bg-white/[0.06] sm:block" aria-hidden />

        <div className="flex flex-wrap items-center gap-1">
          <span className="mr-2 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Risk</span>
          <button type="button" className={cmd} disabled={!!busy} onClick={() => onAction("risk-pause", "/control/manual-pause?enabled=true")}>
            Pause
          </button>
          <button type="button" className={cmd} disabled={!!busy} onClick={() => onAction("risk-clear", "/control/manual-pause?enabled=false")}>
            Clear
          </button>
        </div>

        <div className="flex flex-1 flex-wrap items-center justify-end gap-2 sm:min-w-0">
          <button type="button" className={cmd} disabled={!!busy} onClick={() => onRefresh()}>
            Refresh
          </button>
          <button type="button" className={cmdStop} disabled={!!busy} onClick={() => onAction("stop", "/control/stop")}>
            Stop
          </button>
        </div>
      </div>

      <div className="mt-4 min-h-[1.25rem] space-y-1">
        {busy ? <p className="text-sm text-slate-500">Working — {busy}…</p> : null}
        {lastAction ? <p className="text-sm text-slate-600">{lastAction}</p> : null}
        {err ? <p className="text-sm text-rose-400/90">{err}</p> : null}
      </div>
    </section>
  );
}

type KrakenSkillVariant = "full" | "watch";

const KRAKEN_SESSION_CARDS: {
  id: string;
  actionLabel: string;
  title: string;
  purpose: string;
  bestFor: string;
  symbols: string;
  durationHint: string;
  payload: Record<string, unknown>;
  modes: KrakenSkillVariant[];
}[] = [
  {
    id: "morning-brief",
    actionLabel: "morning-brief",
    title: "Morning Brief",
    purpose: "Plain-English opening read for the watchlist.",
    bestFor: "Start of session",
    symbols: "BTC, ETH, SOL",
    durationHint: "Short read",
    payload: { operation: "morning_brief" },
    modes: ["full", "watch"],
  },
  {
    id: "watch-market",
    actionLabel: "watch-market",
    title: "Watch Market",
    purpose: "Live watch session that logs tape context without trading.",
    bestFor: "Calm monitoring",
    symbols: "BTC, ETH, SOL",
    durationHint: "A few polling cycles",
    payload: { operation: "watch_market" },
    modes: ["full", "watch"],
  },
  {
    id: "paper-session",
    actionLabel: "paper-session",
    title: "Paper Trading Session",
    purpose: "Simulated strategy run with starting capital on the record.",
    bestFor: "Longer desk rehearsal",
    symbols: "Configured in payload",
    durationHint: "Depends on strategy",
    payload: { operation: "paper_trading_session", starting_capital: 10000, strategy: "simple_ma" },
    modes: ["full"],
  },
  {
    id: "buy-drop",
    actionLabel: "buy-drop",
    title: "Buy on Drop Simulation",
    purpose: "Paper path that reacts after a threshold drawdown.",
    bestFor: "Scenario drills",
    symbols: "Default watchlist",
    durationHint: "Single exercise",
    payload: { operation: "buy_on_drop_simulation", drop_percent: 1.5 },
    modes: ["full"],
  },
  {
    id: "price-alert",
    actionLabel: "price-alert",
    title: "Price Alert Session",
    purpose: "Threshold crossings with alert history for review.",
    bestFor: "Lightweight automation",
    symbols: "Configured in session",
    durationHint: "Keeps running until stopped",
    payload: { operation: "price_alert_session" },
    modes: ["full", "watch"],
  },
  {
    id: "verify-cli",
    actionLabel: "verify-cli",
    title: "Verify Kraken CLI",
    purpose: "Check install path for CLI-native flows.",
    bestFor: "Engineers / venue readiness",
    symbols: "—",
    durationHint: "One-off",
    payload: { operation: "install_or_verify_cli" },
    modes: ["full", "watch"],
  },
];

function KrakenSkillActionPanel({
  busy,
  onRun,
  variant = "full",
}: {
  busy: string | null;
  onRun: (label: string, payload: Record<string, unknown>) => void;
  variant?: KrakenSkillVariant;
}) {
  const cardCls =
    "rounded-xl bg-white/[0.03] px-4 py-4 ring-1 ring-white/[0.06] transition hover:bg-white/[0.05] hover:ring-teal-500/25";
  const btnCls =
    "mt-3 rounded-lg bg-teal-500 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-teal-400 disabled:opacity-40";
  const cards = KRAKEN_SESSION_CARDS.filter((c) => c.modes.includes(variant));
  return (
    <section data-testid="kraken-launch-sessions" className={surfaceClass("")} aria-label="Launch a session">
      <SectionHead
        eyebrow="Kraken skills"
        title="Launch a session"
        hint={
          variant === "watch"
            ? "Observational sessions only — switch to Live Paper Trading for simulated fills and lane runs."
            : "Operator launchers with symbols, duration hints, and structured output in each session."
        }
      />
      <div className="grid gap-4 px-8 py-7 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((c) => (
          <div key={c.id} className={cardCls}>
            <p className="text-sm font-semibold text-white">{c.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-slate-500">{c.purpose}</p>
            <p className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Symbols · {c.symbols}</p>
            <p className="mt-1 text-[10px] text-slate-600">Duration · {c.durationHint}</p>
            <p className="mt-1 text-[10px] text-slate-600">Best for · {c.bestFor}</p>
            <button type="button" className={btnCls} disabled={!!busy} onClick={() => onRun(c.actionLabel, c.payload)}>
              Launch
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function KrakenSessionOutputsPanel({ sessions }: { sessions: KrakenSkillSession[] }) {
  const latest = sessions[0];
  if (!latest) return null;
  const outputs = latest.outputs ?? {};
  const tradeLog = Array.isArray(outputs.trade_log) ? (outputs.trade_log as Record<string, unknown>[]) : [];
  const alertHistory = Array.isArray(outputs.alert_history) ? (outputs.alert_history as Record<string, unknown>[]) : [];
  const marketSummary = Array.isArray(outputs.market_summary)
    ? (outputs.market_summary as Record<string, unknown>[])
    : Array.isArray(outputs.watch_log)
      ? (outputs.watch_log as Record<string, unknown>[])
      : [];
  const pnl = num(latest.metrics?.pnl);
  return (
    <section className={surfaceClass("")} aria-labelledby="kraken-session-output-heading">
      <SectionHead
        eyebrow="Session output"
        title="Kraken session results"
        hint="Trade log, PnL, alert history, rationale, and plain-English outcome."
      />
      <div className="grid gap-6 px-8 py-7 lg:grid-cols-2">
        <div className="space-y-4 rounded-xl bg-white/[0.03] p-5 ring-1 ring-white/[0.06]">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">Session summary</p>
          <p className="text-sm text-slate-300">{latest.summary || "—"}</p>
          <p className="text-xs text-slate-500">Status: {latest.status}</p>
          <p className="text-xs text-slate-500">Session rationale: {latest.rationale || "—"}</p>
          <p className="text-sm leading-relaxed text-slate-400">
            Plain English: this session ran <span className="text-slate-200">{latest.operation.replace(/_/g, " ")}</span> for{" "}
            <span className="text-slate-200">{latest.symbols.join(", ")}</span>, then recorded what happened with logs and outputs.
          </p>
          <p className="text-sm text-slate-300">PnL: {pnl != null ? fmtUsd.format(pnl) : "—"}</p>
        </div>
        <div className="space-y-4 rounded-xl bg-white/[0.03] p-5 ring-1 ring-white/[0.06]">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">Session logs</p>
          <div className="max-h-44 space-y-2 overflow-auto">
            {(latest.logs ?? []).map((l, idx) => (
              <p key={`${idx}-${l.at ?? ""}`} className="font-mono text-[11px] text-slate-500">
                {(l.at ?? "").replace("T", " ")} - {l.message ?? "log"}
              </p>
            ))}
          </div>
        </div>
      </div>
      <div className="grid gap-6 px-8 pb-8 lg:grid-cols-3">
        <div className="rounded-xl bg-white/[0.02] p-5 ring-1 ring-white/[0.05]">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">Trade log</p>
          <div className="mt-3 max-h-44 space-y-2 overflow-auto text-xs text-slate-400">
            {tradeLog.length === 0 ? (
              <p>—</p>
            ) : (
              tradeLog.map((t, i) => (
                <p key={i}>
                  {String(t.symbol ?? "")}: enter {String(t.entry_reason ?? "—")} | exit {String(t.exit_reason ?? "—")} | blocked{" "}
                  {String(t.blocked_reason ?? "none")}
                </p>
              ))
            )}
          </div>
        </div>
        <div className="rounded-xl bg-white/[0.02] p-5 ring-1 ring-white/[0.05]">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">Alert history</p>
          <div className="mt-3 max-h-44 space-y-2 overflow-auto text-xs text-slate-400">
            {alertHistory.length === 0 ? <p>—</p> : alertHistory.map((a, i) => <p key={i}>{String(a.symbol)}: {String(a.reason)}</p>)}
          </div>
        </div>
        <div className="rounded-xl bg-white/[0.02] p-5 ring-1 ring-white/[0.05]">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">Market summary</p>
          <div className="mt-3 max-h-44 space-y-2 overflow-auto text-xs text-slate-400">
            {marketSummary.length === 0 ? (
              <p>—</p>
            ) : (
              marketSummary.map((m, i) => <p key={i}>{String(m.symbol)} @ {String(m.price)} ({String(m.source ?? "source")})</p>)
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function TradingLanesPanel({
  lanes,
  laneTrust,
  busy,
  onRun,
  onStart,
  onStop,
  onKrakenBrief,
  variant = "full",
  showcase = false,
}: {
  lanes: TradingLane[];
  laneTrust: LaneTrustSummary[];
  busy: string | null;
  onRun: (laneId: string) => void;
  onStart: (laneId: string) => void;
  onStop: (laneId: string) => void;
  onKrakenBrief: (lane: TradingLane) => void;
  variant?: "full" | "readonly";
  /** Larger narrative framing for live paper operator desk */
  showcase?: boolean;
}) {
  return (
    <section data-testid="trading-lanes-panel" className={surfaceClass("")} aria-labelledby="trading-lanes-heading">
      <SectionHead
        eyebrow={showcase ? "Lane showcase" : "Trading lanes"}
        title={
          variant === "readonly"
            ? "Lanes (read-only)"
            : showcase
              ? "Spot momentum vs tactical futures"
              : "Spot + futures tactical lanes"
        }
        hint={
          variant === "readonly"
            ? "Run lane actions from Live Paper Trading. Here you can still read posture and run a symbol brief."
            : "Two governed paper lanes with different strategy and risk posture — same engine, different risk caps."
        }
      />
      {laneTrust.length > 0 ? (
        <div className="border-b border-white/[0.04] px-8 pb-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
            Lane trust posture
            <Tip text="Per-lane risk outcomes, proof artifacts, and a lane score — complements the global trust tile above." />
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {laneTrust.map((t) => (
              <div
                key={t.lane_id}
                className={`rounded-xl px-4 py-3 ring-1 ${
                  t.market_type === "futures_paper"
                    ? "bg-amber-950/20 ring-amber-500/15"
                    : "bg-teal-950/15 ring-teal-500/15"
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-slate-200">{t.lane_label}</p>
                    <p className="mt-0.5 text-[10px] uppercase tracking-wider text-slate-600">
                      {t.market_type === "futures_paper" ? "Tactical futures (paper)" : "Spot momentum (paper)"}
                    </p>
                  </div>
                  <p className="font-mono text-xs tabular-nums text-teal-200/90" title="Lane trust score 0–100">
                    {t.trust_score_0_100}
                  </p>
                </div>
                <p className="mt-2 text-xs leading-snug text-slate-400">{t.posture_label}</p>
                <p className="mt-2 text-xs leading-relaxed text-slate-600">{t.explainer_one_liner}</p>
                <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 border-t border-white/[0.04] pt-3 text-[11px] text-slate-500">
                  <span>
                    Allowed <span className="tabular-nums text-slate-400">{t.allow_count}</span>
                  </span>
                  <span>
                    Reduced <span className="tabular-nums text-slate-400">{t.reduce_count}</span>
                  </span>
                  <span>
                    Blocked <span className="tabular-nums text-slate-400">{t.block_count}</span>
                  </span>
                  <span>
                    Review <span className="tabular-nums text-slate-400">{t.review_count}</span>
                  </span>
                  <span>
                    Stood aside <span className="tabular-nums text-cyan-200/80">{t.stand_aside_count ?? 0}</span>
                  </span>
                  <span className="text-slate-600">
                    Artifacts <span className="tabular-nums text-slate-400">{t.artifact_count ?? 0}</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className={`grid gap-4 px-8 py-7 lg:grid-cols-2 ${showcase ? "lg:gap-5" : ""}`}>
        {lanes.map((lane) => (
          <article
            key={lane.lane_id}
            data-testid={`lane-card-${lane.lane_id}`}
            className={`rounded-xl p-5 ring-1 ${
              showcase
                ? lane.lane_id === "futures_tactical"
                  ? "bg-gradient-to-b from-amber-950/25 to-black/30 ring-amber-500/20"
                  : "bg-gradient-to-b from-teal-950/20 to-black/30 ring-teal-500/20"
                : "bg-white/[0.03] ring-white/[0.06]"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-base font-semibold text-white">{lane.lane_label}</p>
              <Badge label={lane.status} tone={lane.status === "running" ? "emerald" : "slate"} />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {lane.market_type === "spot" ? "Safer spot lane" : "Tactical futures lane"} · {lane.strategy_family}
            </p>
            <p className="mt-3 text-sm text-slate-400">
              Capital {fmtUsd.format(lane.capital_allocation)} · PnL{" "}
              <span data-testid={`lane-metric-pnl-${lane.lane_id}`}>{fmtUsd.format(lane.performance.pnl_total)}</span> · Drawdown{" "}
              <span data-testid={`lane-metric-drawdown-${lane.lane_id}`}>{fmtUsd.format(lane.performance.drawdown)}</span>
            </p>
            <p className="mt-1 text-xs text-slate-600">
              Last outcome: {lane.last_outcome} · Risk profile: {lane.risk_profile} · Symbols: {lane.default_symbols.join(", ")}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {variant === "full" ? (
                <button
                  type="button"
                  data-testid={`lane-run-once-${lane.lane_id}`}
                  className="rounded-lg bg-teal-500 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-teal-400 disabled:opacity-40"
                  disabled={!!busy}
                  onClick={() => onRun(lane.lane_id)}
                >
                  Run once
                </button>
              ) : null}
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-xs font-medium text-slate-400 ring-1 ring-white/10 hover:bg-white/[0.04] disabled:opacity-40"
                disabled={!!busy}
                onClick={() => onKrakenBrief(lane)}
                title="Kraken Skills morning brief scoped to this lane’s symbols"
              >
                Brief
              </button>
              {variant === "full" ? (
                <>
                  <button
                    type="button"
                    className="rounded-lg px-3 py-2 text-xs font-semibold text-emerald-200 ring-1 ring-emerald-500/30 hover:bg-emerald-500/10 disabled:opacity-40"
                    disabled={!!busy}
                    onClick={() => onStart(lane.lane_id)}
                  >
                    Start
                  </button>
                  <button
                    type="button"
                    className="rounded-lg px-3 py-2 text-xs font-semibold text-rose-200 ring-1 ring-rose-500/30 hover:bg-rose-500/10 disabled:opacity-40"
                    disabled={!!busy}
                    onClick={() => onStop(lane.lane_id)}
                  >
                    Stop
                  </button>
                </>
              ) : null}
            </div>
          </article>
        ))}
      </div>
      <div className="px-8 pb-8">
        <div className="rounded-xl bg-white/[0.02] p-5 ring-1 ring-white/[0.05]">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">Lane comparison</p>
          <div className="mt-4 grid gap-2 text-xs text-slate-400 sm:grid-cols-8">
            <p className="text-slate-600">Lane</p>
            <p className="text-slate-600">Market</p>
            <p className="text-slate-600">Signal/Risk</p>
            <p className="text-slate-600">Last action</p>
            <p className="text-slate-600">PnL</p>
            <p className="text-slate-600">Drawdown</p>
            <p className="text-slate-600">Allow/Reduce/Block</p>
            <p className="text-slate-600">Stood aside</p>
            {lanes.map((lane) => (
              <div key={lane.lane_id} className="contents">
                <p>{lane.lane_label}</p>
                <p>{lane.market_type}</p>
                <p>{lane.strategy_family}</p>
                <p>{lane.last_outcome}</p>
                <p>{fmtUsd.format(lane.performance.pnl_total)}</p>
                <p>{fmtUsd.format(lane.performance.drawdown)}</p>
                <p>
                  {lane.performance.allow_count}/{lane.performance.reduce_count}/{lane.performance.block_count}
                </p>
                <p>{lane.performance.skip_count ?? 0}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function StatTile({
  label,
  value,
  valueClass = "text-white",
  sub,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  valueClass?: string;
  sub?: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="flex min-h-[5.25rem] flex-col justify-center border-t border-white/[0.04] py-5 first:border-t-0 first:pt-0 last:pb-0 sm:border-l sm:border-t-0 sm:py-0 sm:pl-8 sm:first:border-l-0 sm:first:pl-0">
      <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-600">
        {label}
        {hint ? <Tip text={hint} /> : null}
      </p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums tracking-tight sm:text-[1.75rem] sm:leading-none ${valueClass}`}>{value}</p>
      {sub ? <p className="mt-2 text-xs text-slate-600">{sub}</p> : null}
    </div>
  );
}

function ArtifactDeepCard({
  title,
  subtitle,
  kind,
  badge,
  badgeTone = "slate",
  data,
}: {
  title: string;
  subtitle?: string;
  kind: ArtifactKind;
  badge: string | null;
  badgeTone?: "slate" | "emerald" | "sky" | "rose" | "violet";
  data: Record<string, unknown> | null | undefined;
}) {
  const lines = useMemo(() => artifactNarrativeLines(kind, data), [kind, data]);
  const rawJson = useMemo(() => (data && Object.keys(data).length ? JSON.stringify(data, null, 2) : ""), [data]);

  return (
    <article className={`${surfaceClass("")} overflow-hidden`}>
      <div className="border-b border-white/[0.04] px-7 py-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-white">{title}</h3>
            {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
          </div>
          {badge ? <Badge label={badge} tone={badgeTone} /> : null}
        </div>
      </div>
      <div className="space-y-5 px-7 py-6">
        <div className="space-y-2.5">
          {lines.map((line, i) => (
            <p key={i} className="text-sm leading-relaxed text-slate-400">
              {line}
            </p>
          ))}
        </div>
        {rawJson ? (
          <details className="group">
            <summary className="cursor-pointer list-none text-sm font-medium text-slate-600 transition hover:text-slate-400 [&::-webkit-details-marker]:hidden">
              <span className="inline-flex items-center gap-2">
                <span className="inline-block text-slate-700 transition group-open:rotate-90">▸</span>
                View raw JSON
              </span>
            </summary>
            <pre className="mt-4 max-h-56 overflow-auto rounded-lg bg-black/30 p-4 font-mono text-[10px] leading-relaxed text-slate-500">
              {rawJson}
            </pre>
          </details>
        ) : (
          <p className="text-sm text-slate-600">—</p>
        )}
      </div>
    </article>
  );
}

function EvidenceRow({ row, showConnector, timeDisplay }: { row: ActivityItem; showConnector: boolean; timeDisplay: TimeDisplayMode }) {
  const headline = useMemo(
    () => activityHeadline(row.kind, row.summary, row.verdict_or_status),
    [row.kind, row.summary, row.verdict_or_status],
  );
  const explanation = useMemo(() => activityExplanation(row.kind), [row.kind]);
  const tsLabel = useMemo(() => formatOperatorTimestamp(row.timestamp, timeDisplay), [row.timestamp, timeDisplay]);

  return (
    <li className="relative flex gap-0">
      <div className="relative flex w-6 shrink-0 flex-col items-center pt-1">
        <span className="z-10 h-2 w-2 rounded-full bg-slate-500 shadow-[0_0_0_4px_#05080f]" aria-hidden />
        {showConnector ? (
          <span
            className="absolute bottom-0 left-1/2 top-5 w-px -translate-x-1/2 bg-gradient-to-b from-white/[0.12] to-transparent"
            aria-hidden
          />
        ) : null}
      </div>
      <div className="min-w-0 flex-1 pb-12 pl-6">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-600">{proofTrailStageLabel(row.kind)}</span>
          <time className="font-mono text-[11px] text-slate-600" dateTime={row.timestamp}>
            {tsLabel}
          </time>
          {row.verdict_or_status ? (
            <span className="text-[11px] font-medium text-slate-500">{row.verdict_or_status}</span>
          ) : null}
        </div>
        <p className="mt-3 text-base font-medium leading-snug text-slate-100">{headline}</p>
        <p className="mt-2 text-sm leading-relaxed text-slate-500">{explanation}</p>
        <details className="mt-4">
          <summary className="cursor-pointer text-sm text-slate-600 transition hover:text-slate-400">Raw record (JSON / technical)</summary>
          <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-black/25 p-4 font-mono text-[10px] leading-relaxed text-slate-600">
            {row.summary}
          </pre>
        </details>
      </div>
    </li>
  );
}

export default function App() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [krakenSessions, setKrakenSessions] = useState<KrakenSkillSession[]>([]);
  const [lanes, setLanes] = useState<TradingLane[]>([]);
  const [chartPack, setChartPack] = useState<MarketChartPack | null>(null);
  const [chartInterval, setChartInterval] = useState<ChartIntervalId>("1m");
  const [timeDisplay, setTimeDisplayState] = useState<TimeDisplayMode>(() => {
    try {
      return sessionStorage.getItem(TIME_DISPLAY_STORAGE_KEY) === "utc" ? "utc" : "local";
    } catch {
      return "local";
    }
  });
  const persistTimeDisplay = useCallback((m: TimeDisplayMode) => {
    setTimeDisplayState(m);
    try {
      sessionStorage.setItem(TIME_DISPLAY_STORAGE_KEY, m);
    } catch {
      /* ignore */
    }
  }, []);
  const [paperSession, setPaperSession] = useState<PaperSession | null>(null);
  const [productMode, setProductMode] = useState<ProductMode>(() => {
    try {
      const q = new URLSearchParams(window.location.search).get("mode");
      if (q === "paper" || q === "watch" || q === "guided") return q;
    } catch {
      /* ignore */
    }
    return "guided";
  });
  const [lastRefreshedAtIso, setLastRefreshedAtIso] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    try {
      const [o, a, k, l, p] = await Promise.all([
        api<Overview>("/overview"),
        api<ActivityItem[]>("/activity?limit=48"),
        api<KrakenSkillSession[]>("/kraken-skills/sessions?limit=25"),
        api<TradingLane[]>("/lanes"),
        api<PaperSession>("/viz/paper-session"),
      ]);
      setOverview(o);
      setActivity(a);
      setKrakenSessions(k);
      setLanes(l);
      setPaperSession(p);
      const sym = str(o.market_snapshot?.symbol) ?? "BTCUSD";
      const chart = await api<MarketChartPack>(
        `/viz/market-chart?symbol=${encodeURIComponent(sym)}&limit=480&interval=${encodeURIComponent(chartInterval)}`,
      );
      setChartPack(chart);
      setLastRefreshedAtIso(new Date().toISOString());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "fetch failed");
    }
  }, [chartInterval]);

  const refreshMarketSurface = useCallback(async () => {
    try {
      const o = await api<Overview>("/overview");
      setOverview(o);
      const sym = str(o.market_snapshot?.symbol) ?? "BTCUSD";
      const chart = await api<MarketChartPack>(
        `/viz/market-chart?symbol=${encodeURIComponent(sym)}&limit=480&interval=${encodeURIComponent(chartInterval)}`,
      );
      setChartPack(chart);
    } catch {
      /* full refresh still surfaces errors */
    }
  }, [chartInterval]);

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 3000);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    if (productMode !== "paper" && productMode !== "watch") return;
    void refreshMarketSurface();
    const t = setInterval(() => void refreshMarketSurface(), 1100);
    return () => clearInterval(t);
  }, [productMode, refreshMarketSurface]);

  useEffect(() => {
    try {
      const u = new URL(window.location.href);
      u.searchParams.set("mode", productMode);
      window.history.replaceState({}, "", u.toString());
    } catch {
      /* ignore */
    }
  }, [productMode]);

  const sortedTrace = useMemo(() => {
    return [...activity].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [activity]);

  const guidance = useMemo(() => getGuidance(overview, sortedTrace.length), [overview, sortedTrace.length]);

  async function runAction(label: string, path: string) {
    setBusy(label);
    setErr(null);
    setLastAction(null);
    try {
      const base = import.meta.env.VITE_API_BASE_URL as string;
      const res = await fetch(`${base}${path}`, { method: "POST", headers: { "Content-Type": "application/json" } });
      const text = await res.text();
      let msg = `${res.status} ${res.statusText}`;
      try {
        const j = JSON.parse(text) as Record<string, unknown>;
        if (j.error) msg = `Error: ${String(j.error)}`;
        else if (j.autonomous && typeof j.autonomous === "object") {
          const a = j.autonomous as Record<string, unknown>;
          const on = Boolean(a.enabled);
          const cad = typeof a.cadence_seconds === "number" ? `${a.cadence_seconds}s` : "—";
          msg = on ? `Autonomous mode ON (${cad})` : "Autonomous mode OFF";
        }
        else if (typeof j.scenario === "string") {
          const title = SCENARIO_MESSAGES[j.scenario] ?? j.scenario;
          if (j.skipped) msg = `${title} — stood aside this cycle (no trade; not a hard block).`;
          else if (j.blocked) msg = `${title} — stopped at risk (see pipeline + proof trail).`;
          else if (j.escalated) msg = `${title} — escalated for review (no fill).`;
          else msg = `${title} — full governed path updated (${String(j.execution_status ?? "ok")}).`;
        } else if (j.skipped) msg = "Cycle complete — stood aside (no trade; not a hard block).";
        else if (j.blocked) msg = "Cycle complete — risk router blocked (see evidence chain).";
        else if (j.escalated) msg = "Cycle complete — escalated for review (no fill).";
        else if (j.ok === false) msg = `Response: ${text.slice(0, 200)}`;
        else msg = "OK — governed pipeline updated.";
      } catch {
        if (!res.ok) msg = text || msg;
      }
      setLastAction(msg);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "request failed");
    } finally {
      setBusy(null);
    }
    void refresh().catch(() => {});
  }

  async function runKrakenSkill(label: string, payload: Record<string, unknown>) {
    setBusy(label);
    setErr(null);
    setLastAction(null);
    try {
      const session = await postJson<KrakenSkillSession>("/kraken-skills/run", payload);
      setLastAction(`Kraken session #${session.id} complete: ${session.summary}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "kraken skill failed");
    } finally {
      setBusy(null);
    }
    void refresh().catch(() => {});
  }

  async function runLaneAction(label: string, path: string) {
    setBusy(label);
    setErr(null);
    try {
      await api<Record<string, unknown>>(path, { method: "POST" });
      setLastAction(`Lane action complete: ${label}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "lane action failed");
    } finally {
      setBusy(null);
    }
    void refresh().catch(() => {});
  }

  const mode = overview?.control.mode ?? "—";
  const verdict = str(overview?.latest_risk?.verdict) ?? "—";
  const execStatus = str(overview?.latest_execution?.status) ?? "—";
  const perf = overview?.latest_performance;
  const equity = num(perf?.equity);
  const pnlTotal = num(perf?.pnl_total);
  const pnlDaily = num(perf?.pnl_daily);
  const drawdown = num(perf?.drawdown);
  const position = num(perf?.position_notional);
  const peakHint = equity != null && drawdown != null ? equity + drawdown : null;
  const ddPct = peakHint && peakHint > 0 && drawdown != null ? (drawdown / peakHint) * 100 : null;

  const sig = overview?.latest_signal;
  const risk = overview?.latest_risk;
  const intent = overview?.latest_intent;
  const ex = overview?.latest_execution;

  const riskBadgeTone = verdict !== "—" ? riskTone(verdict) : "slate";
  const execBadgeTone = execStatus !== "—" ? execTone(execStatus) : "slate";

  const tapeCapturedAt = str(
    overview?.market_snapshot && typeof overview.market_snapshot === "object"
      ? (overview.market_snapshot as { captured_at?: unknown }).captured_at
      : undefined,
  );

  const laneScopeLabel = useMemo(() => {
    const runningLanes = lanes.filter((l) => l.status === "running");
    if (runningLanes.length > 0) {
      const labels = runningLanes.map((l) => l.lane_label || l.lane_id).filter(Boolean) as string[];
      if (labels.length === 1) return labels[0] ?? "Lane";
      if (labels.length > 1) return labels.join(" · ");
    }
    if (overview?.autonomous?.enabled) return "Core desk loop";
    const scoped = intent?.lane_label || intent?.lane_id;
    if (scoped) return String(scoped);
    return "Desk idle";
  }, [lanes, overview?.autonomous?.enabled, intent?.lane_label, intent?.lane_id]);

  const currentStorySentence = useMemo(() => livePaperCurrentStorySentence(overview), [overview]);

  const silentCycleFpRef = useRef<string | null>(null);
  const [silentCycleDelta, setSilentCycleDelta] = useState(
    "Showing the latest desk state — refresh or run again to compare the next update.",
  );

  useEffect(() => {
    if (productMode !== "paper") {
      silentCycleFpRef.current = null;
      return;
    }
    const rp = overview?.latest_risk as { id?: unknown } | undefined;
    const exr = overview?.latest_execution as { id?: unknown } | undefined;
    const rid = typeof rp?.id === "number" ? rp.id : -1;
    const eid = typeof exr?.id === "number" ? exr.id : -1;
    const tl = sortedTrace.length;
    const fp = `${rid}|${eid}|${tl}`;
    const prev = silentCycleFpRef.current;
    silentCycleFpRef.current = fp;
    if (prev === null) {
      setSilentCycleDelta("Showing the latest desk state — refresh or run again to compare the next update.");
      return;
    }
    if (prev === fp) {
      setSilentCycleDelta("No new trade or ledger change since the last refresh.");
      return;
    }
    const [pr, pe, pt] = prev.split("|");
    const msgs: string[] = [];
    if (pr !== String(rid)) msgs.push("New safety verdict on the ledger.");
    if (pe !== String(eid)) msgs.push("Execution row changed (fill, reject, or new row).");
    if (pt !== String(tl) && tl > Number(pt)) msgs.push(`Proof trail +${tl - Number(pt)} row(s).`);
    setSilentCycleDelta(msgs.length ? msgs.join(" ") : "Latest view updated.");
  }, [productMode, overview, sortedTrace.length]);

  const silentStripMarket = useMemo(() => {
    const snap = overview?.market_snapshot;
    if (snap && typeof snap === "object") {
      const sym = str(snap.symbol) ?? "—";
      const vol = snap.volatility_flag === true;
      return `${sym.replace("USD", "/USD")} · ${vol ? "Volatile" : "Calm"}`;
    }
    const a = str(sig?.asset);
    return a ? `${a.replace("USD", "/USD")} · snapshot pending` : "—";
  }, [overview?.market_snapshot, sig?.asset]);

  const silentStripBot = useMemo(() => {
    if (!sig) return "—";
    const st = str(sig.signal_type) ?? "—";
    const a = str(sig.asset) ?? "";
    return a ? `${st} · ${a.replace("USD", "/USD")}` : st;
  }, [sig]);

  const silentStripRisk = verdict;
  const silentStripExec = useMemo(() => {
    if (verdict === "skip" || verdict === "block") {
      return ex ? str(ex.status) ?? "—" : "— (none)";
    }
    return ex ? str(ex.status) ?? "—" : "—";
  }, [verdict, ex]);

  const silentStripReason = useMemo(() => {
    const r = str(risk?.reasons);
    return r ? truncSilent(r, 100) : "—";
  }, [risk?.reasons]);

  const proofTrailSection = (
    <section id="proof-trail" className={`${surfaceClass("")} scroll-mt-28`} aria-label="Proof trail and trust surface">
      <div className="border-b border-white/[0.04] px-8 pb-8 pt-10">
        <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Verification · Trust surface
          <Tip text="Each row is a durable record from a pipeline stage — same story as the API artifacts and CLI draft above." />
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">Proof trail</h2>
        <p data-testid="proof-trail-count" className="mt-1 font-mono text-xs text-slate-500">
          Proof events loaded: {sortedTrace.length}
        </p>
        <p className="mt-1 text-sm font-medium text-slate-600">Human-readable first · technical stage label in small type</p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-500">
          Each row is a moment in time. Read the headline, skim the explanation, open raw JSON only when you need field-level detail.
        </p>
      </div>
      <div className="px-8 pb-12 pt-2">
        <p className="max-w-2xl text-sm leading-relaxed text-slate-600">
          Flow: trading idea → safety check → committed plan → execution result — same order as the pipeline and system status strip (venue
          surface + identity hooks).
        </p>
        <p className="mt-4 font-mono text-[11px] text-slate-700">
          {ARTIFACT_ORDER.map((k, idx) => (
            <span key={k}>
              {idx + 1}. {proofTrailStageLabel(k)}
              {idx < ARTIFACT_ORDER.length - 1 ? <span className="text-slate-800"> · </span> : null}
            </span>
          ))}
        </p>
        <ul className="mt-12">
          {sortedTrace.map((row, idx) => (
            <EvidenceRow key={row.id} row={row} showConnector={idx < sortedTrace.length - 1} timeDisplay={timeDisplay} />
          ))}
        </ul>
        {sortedTrace.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-base font-medium text-slate-300">No proof events yet</p>
            <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-600">
              The trail fills in after you <strong className="text-slate-400">Seed demo data</strong> and{" "}
              <strong className="text-slate-400">Run one cycle</strong>. That’s the fastest way to light up the full path.
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );

  const deepArtifactsSection = (
    <section className="space-y-8 pt-4" aria-labelledby="technical-heading">
      <div className="px-1">
        <p id="technical-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Under the hood
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">
          Latest artifacts
          <Tip text="Structured payloads for engineers who want field-level proof — everyday readers can stay in the Proof trail." />
        </h2>
        <p className="mt-2 max-w-lg text-sm text-slate-600">
          Plain-language recap first; open “View raw JSON” only when you need exact fields.
        </p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <ArtifactDeepCard
          title="Trading idea"
          subtitle="Strategy signal · latest record"
          kind="signal"
          badge={sig ? (str(sig.signal_type) ?? null) : null}
          data={sig}
        />
        <ArtifactDeepCard
          title="Safety check"
          subtitle="Risk router · policy verdict"
          kind="risk"
          badge={risk ? (str(risk.verdict) ?? null) : null}
          badgeTone={risk ? riskBadgeTone : "slate"}
          data={risk}
        />
        <ArtifactDeepCard
          title="Committed trade plan"
          subtitle="Signed intent · cryptographic commitment"
          kind="intent"
          badge={intent ? (str(intent.status) ?? null) : null}
          data={intent}
        />
        <ArtifactDeepCard
          title="Execution result"
          subtitle="Venue path · simulated fill; Kraken draft in system status"
          kind="execution"
          badge={ex ? (str(ex.status) ?? null) : null}
          badgeTone={ex ? execBadgeTone : "slate"}
          data={ex}
        />
      </div>
    </section>
  );

  const integrationSection = (
    <section className="space-y-4" aria-label="Integration surface">
      <p className="px-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
        {productMode === "watch" ? "Trust & source details" : productMode === "paper" ? "System evidence" : "Integration surface"}
        <Tip text="Identity and trust metrics, Kraken-shaped venue boundary, and a short checklist of what’s wired for this session." />
      </p>
      <div className="grid gap-6 lg:grid-cols-3">
        <AgentIdentityTrustPanel overview={overview} />
        <KrakenExecutionAdapterPanel overview={overview} />
        <ChallengeFitPanel overview={overview} />
      </div>
    </section>
  );

  const performanceSection = (
    <section className={surfaceClass("")} aria-label="Performance and market snapshot">
      <SectionHead eyebrow="Portfolio &amp; market" title="Performance" hint="Paper book and reference tape" />
      <div className="grid gap-12 px-8 py-10 lg:grid-cols-3 lg:gap-12">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-600">Portfolio</p>
          {equity != null ? (
            <dl className="mt-6 space-y-5 text-sm">
              <div className="flex justify-between gap-6">
                <dt className="text-slate-600">Equity</dt>
                <dd className="tabular-nums text-lg font-medium text-white">{fmtUsd.format(equity)}</dd>
              </div>
              <div className="flex justify-between gap-6">
                <dt className="text-slate-600">P&amp;L (total)</dt>
                <dd
                  className={`tabular-nums text-lg font-medium ${
                    pnlTotal != null && pnlTotal < 0 ? "text-rose-200" : pnlTotal != null && pnlTotal > 0 ? "text-emerald-200" : "text-white"
                  }`}
                >
                  {pnlTotal != null ? fmtUsd.format(pnlTotal) : "—"}
                </dd>
              </div>
              <div className="flex justify-between gap-6">
                <dt className="text-slate-600">Δ last snap</dt>
                <dd className={`tabular-nums ${pnlDaily != null && pnlDaily < 0 ? "text-rose-200/90" : "text-slate-300"}`}>
                  {pnlDaily != null ? fmtUsd.format(pnlDaily) : "—"}
                </dd>
              </div>
              <div className="flex justify-between gap-6">
                <dt className="text-slate-600">Drawdown</dt>
                <dd className={`tabular-nums ${drawdown != null && drawdown < 0 ? "text-amber-200/90" : "text-slate-200"}`}>
                  {drawdown != null ? fmtUsd.format(drawdown) : "—"}
                </dd>
              </div>
              {ddPct != null ? (
                <div>
                  <div className="mb-2 flex justify-between text-xs text-slate-600">
                    <span>Vs peak hint</span>
                    <span className="tabular-nums">{ddPct.toFixed(2)}%</span>
                  </div>
                  <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
                    <div
                      className="h-full rounded-full bg-white/20 transition-all duration-500"
                      style={{ width: `${Math.min(100, ddPct)}%` }}
                    />
                  </div>
                </div>
              ) : null}
              <div className="flex justify-between gap-6 pt-2">
                <dt className="text-slate-600">Position</dt>
                <dd className="tabular-nums text-slate-300">{position != null ? fmtUsd.format(position) : "—"}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-6 text-sm text-slate-600">No performance row yet — seed the demo.</p>
          )}
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-600">Reference snapshot</p>
          <div className="mt-6">
            {overview?.market_snapshot ? (
              <dl className="space-y-6 text-sm">
                <div>
                  <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Symbol</dt>
                  <dd className="mt-2 text-2xl font-semibold tracking-tight text-white">{str(overview.market_snapshot.symbol)}</dd>
                </div>
                <div>
                  <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Price</dt>
                  <dd className="mt-2 text-2xl font-semibold tabular-nums tracking-tight text-slate-100">
                    {num(overview.market_snapshot.price)?.toLocaleString() ?? "—"}
                  </dd>
                </div>
                {num(overview.market_snapshot.bid) != null && num(overview.market_snapshot.ask) != null ? (
                  <div className="flex gap-8">
                    <div>
                      <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Bid</dt>
                      <dd className="mt-2 font-mono text-lg tabular-nums text-slate-200">{num(overview.market_snapshot.bid)?.toLocaleString()}</dd>
                    </div>
                    <div>
                      <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Ask</dt>
                      <dd className="mt-2 font-mono text-lg tabular-nums text-slate-200">{num(overview.market_snapshot.ask)?.toLocaleString()}</dd>
                    </div>
                  </div>
                ) : null}
                <div>
                  <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Tape source</dt>
                  <dd
                    data-testid="market-snapshot-source"
                    data-raw-source={str(overview.market_snapshot.source) ?? ""}
                    className="mt-2 text-sm font-medium text-slate-400"
                  >
                    {tapeSourceLabel(str(overview.market_snapshot.source))}
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Captured</dt>
                  <dd
                    data-testid="reference-snapshot-captured-at"
                    className="mt-2 font-mono text-xs text-slate-600"
                  >
                    {typeof overview.market_snapshot.captured_at === "string"
                      ? formatOperatorTimestamp(overview.market_snapshot.captured_at, timeDisplay)
                      : "—"}
                  </dd>
                </div>
                {overview.market_snapshot.volatility_flag ? (
                  <p className="text-sm text-rose-300/90">Volatility elevated — risk router may block.</p>
                ) : null}
              </dl>
            ) : (
              <p className="text-sm text-slate-600">No snapshot — seed the demo.</p>
            )}
          </div>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-600">Top pairs (ingested)</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            BTC/USD, ETH/USD, SOL/USD — last values stored for this session. Kraken mode pulls live public ticker; demo mode uses synthetic
            snapshots.
          </p>
          <div className="mt-6 space-y-3">
            {(overview?.top_markets?.length ?? 0) > 0 ? (
              overview!.top_markets!.map((row) => (
                <div
                  key={row.symbol}
                  className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-white/[0.03] px-4 py-3 ring-1 ring-white/[0.06]"
                >
                  <span className="font-mono text-sm font-semibold text-white">{row.symbol.replace("USD", "/USD")}</span>
                  <span className="tabular-nums text-lg font-medium text-slate-100">{row.price.toLocaleString()}</span>
                  <span className="w-full text-[10px] font-medium uppercase tracking-wider text-slate-600 sm:w-auto">
                    {tapeSourceLabel(row.source)}
                    {row.captured_at ? (
                      <span className="mt-1 block font-mono normal-case text-slate-500">
                        {formatOperatorTimestamp(row.captured_at, timeDisplay)}
                      </span>
                    ) : null}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-600">No multi-pair rows yet — seed or run a cycle (Kraken mode ingests all three).</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );

  const executiveSection = (
    <section aria-label="Executive status">
      <p className="mb-4 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
        At a glance
        <Tip text="Numbers update every few seconds. They describe the simulated portfolio, not a real brokerage account." />
      </p>
      {!overview?.latest_risk ? (
        <div className="mb-4 rounded-xl bg-white/[0.03] px-5 py-4 text-sm leading-relaxed text-slate-400 ring-1 ring-white/[0.06]">
          Nothing to show yet—load the demo first. Use <strong className="font-medium text-slate-200">Seed demo data</strong> in the guided panel
          above, then <strong className="font-medium text-slate-200">Run one cycle</strong>.
        </div>
      ) : null}
      <div className="flex flex-col divide-y divide-white/[0.04] rounded-2xl bg-white/[0.02] px-6 py-2 ring-1 ring-white/[0.04] sm:flex-row sm:divide-x sm:divide-y-0 sm:px-0 sm:py-8">
        <StatTile
          label="Equity"
          value={equity != null ? fmtUsd.format(equity) : "—"}
          valueClass="text-white"
          hint="Total simulated portfolio value for this session."
        />
        <StatTile
          label="P&amp;L"
          value={pnlTotal != null ? fmtUsd.format(pnlTotal) : "—"}
          valueClass={
            pnlTotal != null && pnlTotal < 0 ? "text-rose-200" : pnlTotal != null && pnlTotal > 0 ? "text-emerald-200" : "text-white"
          }
          sub={pnlDaily != null ? `Δ snap ${fmtUsd.format(pnlDaily)}` : undefined}
          hint="Profit or loss since this session started — simulated only."
        />
        <StatTile
          label="Drawdown"
          value={drawdown != null ? fmtUsd.format(drawdown) : "—"}
          valueClass={drawdown != null && drawdown < 0 ? "text-amber-200/90" : "text-white"}
          sub={ddPct != null ? `${ddPct.toFixed(2)}% vs peak hint` : undefined}
          hint="How far below a recent high the paper portfolio dipped."
        />
        <StatTile
          label="Mode"
          value={mode}
          valueClass={modeValueClass(mode)}
          sub={overview?.control.manual_pause ? "Manual risk pause" : undefined}
          hint="Whether the engine is running, paused for stepping, or stopped—controls are in the command bar."
        />
        <StatTile
          label="Risk state"
          value={verdict}
          valueClass={verdict === "—" ? "text-slate-200" : riskValueClass(verdict)}
          hint="Verdict from the newest risk decision — same cycle as pipeline, plain-English story, and execution tile."
        />
        <StatTile
          label="Execution"
          value={execStatus}
          valueClass={execStatus === "—" ? "text-slate-200" : execValueClass(execStatus)}
          hint="Paper ledger for the latest intent on that same risk cycle — filled, rejected, or none if the desk stood aside or blocked."
        />
      </div>
    </section>
  );

  return (
    <div className="relative min-h-screen bg-[#05080f] text-slate-200">
      <div className="pointer-events-none fixed inset-0 vt-grid-bg opacity-[0.22]" aria-hidden />
      <div className="pointer-events-none fixed inset-0 vt-hero-glow" aria-hidden />

      <GlobalShell
        err={err}
        busy={busy}
        onRefresh={() => void refresh()}
        productMode={productMode}
        onMode={setProductMode}
        safetyStrip={overview?.safety_strip}
        autonomous={overview?.autonomous}
        laneScopeLabel={laneScopeLabel}
        lastRefreshedAtIso={lastRefreshedAtIso}
        tapeCapturedAt={tapeCapturedAt ?? undefined}
        timeDisplay={timeDisplay}
        contentWide={productMode === "paper"}
      >
        <main className={`relative pb-20 pt-4 sm:pt-6 ${productMode === "paper" ? "space-y-8" : "space-y-12"}`}>
        {/* Product headline — compact in live paper so the hero chart leads */}
        <section className={`space-y-4 ${productMode === "paper" ? "max-w-3xl" : ""}`}>
          <p className="text-[11px] font-medium uppercase tracking-[0.28em] text-slate-600">
            {productMode === "paper" ? (
              <>
                Live paper trading desk
                <Tip text="No live orders in this build — balances and fills are simulated so you can learn the controls safely." />
              </>
            ) : (
              <>
                Operator console · Simulated execution
                <Tip text="No live orders in this build — balances and fills are simulated so you can learn the controls safely." />
              </>
            )}
          </p>
          <h1
            className={`font-semibold tracking-[-0.03em] text-white ${
              productMode === "paper" ? "text-3xl sm:text-4xl sm:leading-tight" : "text-5xl sm:text-6xl sm:leading-[1.05]"
            }`}
          >
            VeriTrade
          </h1>
          <p
            className={`max-w-2xl leading-relaxed text-slate-400 ${
              productMode === "paper" ? "text-sm sm:text-base" : "text-lg sm:text-xl"
            }`}
          >
            {productMode === "paper" ? (
              <>
                Chart-first operator read: live tape, current desk decision, then controls. Proof and presets stay one expand away — no narration
                required.
              </>
            ) : (
              <>
                A governed trading desk: propose an idea, run automatic safety checks, lock a signed plan, record a simulated fill — with Kraken-style
                routing and agent identity surfaced so you see how production would be wired.
              </>
            )}
          </p>
        </section>

        {productMode === "guided" ? (
          <>
            <div id="vt-guided" className="scroll-mt-24 space-y-10 rounded-2xl ring-1 ring-teal-500/25 sm:p-5">
              <QuickStartStrip overview={overview} traceLen={sortedTrace.length} />
              <GuidedNextPanel guidance={guidance} busy={busy} onPost={(label, path) => void runAction(label, path)} />
              <GuidedDemoSteps />
            </div>
            <LiveTapeChartPanel
              chartPack={chartPack}
              chartInterval={chartInterval}
              onChartInterval={setChartInterval}
              timeDisplay={timeDisplay}
              onTimeDisplayChange={persistTimeDisplay}
              positionNotional={position}
              sourceLabel={overview?.safety_strip?.market_mode_label}
              emphasize={false}
              sectionId="vt-watch"
              layout="default"
            />
            <ScenarioPresetsBar
              busy={busy}
              overview={overview}
              onScenario={(label, path) => void runAction(label, path)}
            />
            <CommandSurface
              busy={busy}
              lastAction={lastAction}
              err={err}
              onAction={(l, p) => void runAction(l, p)}
              onRefresh={() => void refresh()}
            />
            {proofTrailSection}
            <EvidenceCollapsible
              defaultOpen={false}
              eyebrow="More detail"
              title="Pipeline, lanes, desk tools, and raw artifacts"
              subtitle="Same engine as always — open when you want integration tiles, history, Kraken sessions, and JSON."
            >
              <ChallengeStrip challenge={overview?.challenge} />
              {integrationSection}
              <CycleHistoryPanel overview={overview} timeDisplay={timeDisplay} />
              <PipelineRail overview={overview} />
              <AutonomousStatePanel
                overview={overview}
                paperSession={paperSession}
                busy={busy}
                emphasize={false}
                timeDisplay={timeDisplay}
                variant="readonly"
                onAction={(l, p) => void runAction(l, p)}
              />
              <TradingLanesPanel
                lanes={lanes}
                laneTrust={overview?.lane_trust ?? []}
                busy={busy}
                variant="readonly"
                onRun={(laneId) => void runLaneAction(`run-${laneId}`, `/lanes/${laneId}/run-once`)}
                onStart={(laneId) => void runLaneAction(`start-${laneId}`, `/lanes/${laneId}/start`)}
                onStop={(laneId) => void runLaneAction(`stop-${laneId}`, `/lanes/${laneId}/stop`)}
                onKrakenBrief={(lane) =>
                  void runKrakenSkill(`brief-${lane.lane_id}`, {
                    operation: "morning_brief",
                    lane_id: lane.lane_id,
                    symbols: lane.default_symbols,
                  })
                }
              />
              <PaperSessionSummaryPanel paper={paperSession} />
              <KrakenSkillActionPanel busy={busy} variant="full" onRun={(label, payload) => void runKrakenSkill(label, payload)} />
              <KrakenSessionOutputsPanel sessions={krakenSessions} />
              <PlainStoryPanel overview={overview} chartContext={chartPack?.context ?? null} />
              <WhyTradePanel overview={overview} />
              {executiveSection}
              {performanceSection}
              {deepArtifactsSection}
            </EvidenceCollapsible>
          </>
        ) : null}

        {productMode === "watch" ? (
          <>
            <LiveTapeChartPanel
              chartPack={chartPack}
              chartInterval={chartInterval}
              onChartInterval={setChartInterval}
              timeDisplay={timeDisplay}
              onTimeDisplayChange={persistTimeDisplay}
              positionNotional={position}
              sourceLabel={overview?.safety_strip?.market_mode_label}
              emphasize
              sectionId="vt-watch"
              layout="workstation"
            />
            <TopPairsStrip overview={overview} timeDisplay={timeDisplay} />
            <KrakenSkillActionPanel busy={busy} variant="watch" onRun={(label, payload) => void runKrakenSkill(label, payload)} />
            <KrakenSessionOutputsPanel sessions={krakenSessions} />
            <AutonomousStatePanel
              overview={overview}
              paperSession={paperSession}
              busy={busy}
              emphasize={false}
              timeDisplay={timeDisplay}
              variant="readonly"
              onAction={(l, p) => void runAction(l, p)}
            />
            <TradingLanesPanel
              lanes={lanes}
              laneTrust={overview?.lane_trust ?? []}
              busy={busy}
              variant="readonly"
              onRun={(laneId) => void runLaneAction(`run-${laneId}`, `/lanes/${laneId}/run-once`)}
                onStart={(laneId) => void runLaneAction(`start-${laneId}`, `/lanes/${laneId}/start`)}
                onStop={(laneId) => void runLaneAction(`stop-${laneId}`, `/lanes/${laneId}/stop`)}
                onKrakenBrief={(lane) =>
                  void runKrakenSkill(`brief-${lane.lane_id}`, {
                    operation: "morning_brief",
                    lane_id: lane.lane_id,
                    symbols: lane.default_symbols,
                  })
                }
            />
            {executiveSection}
            <CommandSurface
              busy={busy}
              lastAction={lastAction}
              err={err}
              onAction={(l, p) => void runAction(l, p)}
              onRefresh={() => void refresh()}
            />
            <EvidenceCollapsible
              defaultOpen={false}
              eyebrow="Evidence layer"
              title="Proof trail, presets, integration, and performance"
              subtitle="Expand for the full audit path and portfolio snapshot."
            >
              <ChallengeStrip challenge={overview?.challenge} />
              <ScenarioPresetsBar
                busy={busy}
                overview={overview}
                onScenario={(label, path) => void runAction(label, path)}
              />
              {integrationSection}
              <CycleHistoryPanel overview={overview} timeDisplay={timeDisplay} />
              <PipelineRail overview={overview} />
              <PaperSessionSummaryPanel paper={paperSession} />
              <PlainStoryPanel overview={overview} chartContext={chartPack?.context ?? null} />
              <WhyTradePanel overview={overview} />
              {performanceSection}
              {proofTrailSection}
              {deepArtifactsSection}
            </EvidenceCollapsible>
          </>
        ) : null}

        {productMode === "paper" ? (
          <>
            <div id="vt-paper" className="scroll-mt-24 space-y-5 sm:space-y-6">
              <LivePaperHeroStatusRail
                safetyStrip={overview?.safety_strip}
                autonomous={overview?.autonomous}
                laneScopeLabel={laneScopeLabel}
                lastRefreshedAtIso={lastRefreshedAtIso}
                tapeCapturedAt={tapeCapturedAt ?? undefined}
                timeDisplay={timeDisplay}
              />
              <div className="grid min-h-0 gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(260px,22rem)] xl:items-stretch xl:gap-6">
                <LiveTapeChartPanel
                  chartPack={chartPack}
                  chartInterval={chartInterval}
                  onChartInterval={setChartInterval}
                  timeDisplay={timeDisplay}
                  onTimeDisplayChange={persistTimeDisplay}
                  positionNotional={position}
                  sourceLabel={overview?.safety_strip?.market_mode_label}
                  emphasize
                  layout="workstation"
                />
                <LivePaperDecisionStack
                  story={currentStorySentence}
                  marketLine={silentStripMarket}
                  botLine={silentStripBot}
                  riskLine={silentStripRisk}
                  execLine={silentStripExec}
                  reasonLine={silentStripReason}
                  cycleDelta={silentCycleDelta}
                  riskClassName={verdict === "—" ? "text-slate-200" : riskValueClass(verdict)}
                  execClassName={execStatus === "—" ? "text-slate-200" : execValueClass(execStatus)}
                />
              </div>

              <div className="rounded-2xl border border-white/[0.07] bg-gradient-to-b from-white/[0.035] to-black/20 p-4 ring-1 ring-white/[0.05] sm:p-5">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-600">Operator strip</p>
                <div className="mt-4 space-y-5">
                  {executiveSection}
                  <AutonomousStatePanel
                    overview={overview}
                    paperSession={paperSession}
                    busy={busy}
                    emphasize={false}
                    timeDisplay={timeDisplay}
                    variant="full"
                    layout="compact"
                    onAction={(l, p) => void runAction(l, p)}
                  />
                  <CommandSurface
                    busy={busy}
                    lastAction={lastAction}
                    err={err}
                    onAction={(l, p) => void runAction(l, p)}
                    onRefresh={() => void refresh()}
                    hideDemoPresets
                    compact
                  />
                </div>
              </div>

              <TradingLanesPanel
                lanes={lanes}
                laneTrust={overview?.lane_trust ?? []}
                busy={busy}
                variant="full"
                showcase
                onRun={(laneId) => void runLaneAction(`run-${laneId}`, `/lanes/${laneId}/run-once`)}
                onStart={(laneId) => void runLaneAction(`start-${laneId}`, `/lanes/${laneId}/start`)}
                onStop={(laneId) => void runLaneAction(`stop-${laneId}`, `/lanes/${laneId}/stop`)}
                onKrakenBrief={(lane) =>
                  void runKrakenSkill(`brief-${lane.lane_id}`, {
                    operation: "morning_brief",
                    lane_id: lane.lane_id,
                    symbols: lane.default_symbols,
                  })
                }
              />
            </div>

            <EvidenceCollapsible
              defaultOpen={false}
              eyebrow="Proof &amp; trust"
              title="Validation, pipeline, and evidence chain"
              subtitle="Proof trail, structured artifacts, integration posture, and challenge context — credibility without crowding the tape."
            >
              <ChallengeStrip challenge={overview?.challenge} />
              <PipelineRail overview={overview} />
              {integrationSection}
              {proofTrailSection}
              {deepArtifactsSection}
            </EvidenceCollapsible>

            <EvidenceCollapsible
              defaultOpen={false}
              tone="secondary"
              eyebrow="More tools"
              title="Scenarios, lane rationale, Kraken sessions, and audit trail"
              subtitle="Preset markets, deeper “why” copy, long-run session narrative, cycle history, and portfolio snapshot — open when you need them."
            >
              <ScenarioPresetsBar
                busy={busy}
                overview={overview}
                onScenario={(label, path) => void runAction(label, path)}
              />
              <WhyTradePanel overview={overview} />
              <PaperSessionSummaryPanel paper={paperSession} />
              <KrakenSkillActionPanel busy={busy} variant="full" onRun={(label, payload) => void runKrakenSkill(label, payload)} />
              <KrakenSessionOutputsPanel sessions={krakenSessions} />
              <PlainStoryPanel overview={overview} chartContext={chartPack?.context ?? null} />
              <CycleHistoryPanel overview={overview} timeDisplay={timeDisplay} />
              {performanceSection}
            </EvidenceCollapsible>
          </>
        ) : null}

        <footer className="border-t border-white/[0.04] pt-12 text-center text-[11px] text-slate-700">
          VeriTrade · governed trading console · simulated execution by default
        </footer>
      </main>
      </GlobalShell>
    </div>
  );
}
