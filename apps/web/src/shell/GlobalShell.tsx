import type { ReactNode } from "react";
import { formatOperatorTimestamp, type TimeDisplayMode } from "../operatorTime";
import { Badge, surfaceClass, Tip } from "../dashboard/uiPrimitives";
import type { ProductMode } from "../dashboard/modeCopy";
import { MODE_META, PRODUCT_MODE_ORDER } from "../dashboard/modeCopy";

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

type AutonomousStatus = {
  enabled: boolean;
  cadence_seconds: number;
  last_cycle_at: string | null;
};

export function GlobalShell({
  err,
  busy,
  onRefresh,
  productMode,
  onMode,
  safetyStrip,
  autonomous,
  laneScopeLabel,
  lastRefreshedAtIso,
  tapeCapturedAt,
  timeDisplay,
  contentWide,
  children,
}: {
  err: string | null;
  busy: string | null;
  onRefresh: () => void;
  productMode: ProductMode;
  onMode: (m: ProductMode) => void;
  safetyStrip: SafetyStrip | null | undefined;
  autonomous: AutonomousStatus | null | undefined;
  /** Lane runner, core loop, or last scoped cycle — from App for one coherent status line */
  laneScopeLabel: string;
  lastRefreshedAtIso: string | null;
  tapeCapturedAt: string | null | undefined;
  timeDisplay: TimeDisplayMode;
  /** Wider content column for chart-first operator layouts */
  contentWide?: boolean;
  children: ReactNode;
}) {
  const s = safetyStrip;
  const auto = autonomous;

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-white/[0.04] bg-[#05080f]/80 backdrop-blur-xl backdrop-saturate-150">
        <div className={`mx-auto flex flex-col gap-3 px-4 py-3.5 sm:px-6 ${contentWide ? "max-w-[min(100%,92rem)]" : "max-w-6xl"}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <span className="text-[13px] font-semibold tracking-tight text-white">VeriTrade</span>
              <p className="mt-0.5 truncate text-[10px] font-medium uppercase tracking-[0.18em] text-slate-600">
                Operator workstation · simulated execution by default
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-4">
              <span
                className={`hidden text-[10px] font-medium uppercase tracking-[0.2em] sm:inline ${err ? "text-rose-400/90" : "text-slate-600"}`}
              >
                {err ? "Degraded" : "Live"}
              </span>
              <button
                type="button"
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-300 disabled:opacity-40"
                disabled={!!busy}
                onClick={() => onRefresh()}
              >
                Refresh
              </button>
            </div>
          </div>

          {s ? (
            <div
              className="flex flex-col gap-2 border-t border-white/[0.04] pt-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-3 sm:gap-y-2 sm:border-t-0 sm:pt-0"
              aria-label="Global status"
            >
              <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-600">Status</span>
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  data-testid="market-mode-badge"
                  label={s.market_mode_label}
                  tone={s.market_data_mode === "demo" ? "slate" : "sky"}
                />
                <span data-testid="market-data-mode" className="sr-only">
                  {s.market_data_mode}
                </span>
                <Badge data-testid="execution-mode-badge" label={s.execution_mode} tone="indigo" />
                <Badge
                  label={auto?.enabled ? `Autonomous ON · ${auto.cadence_seconds}s` : "Autonomous idle"}
                  tone={auto?.enabled ? "emerald" : "slate"}
                />
                <Badge label={laneScopeLabel} tone="violet" />
                {lastRefreshedAtIso ? (
                  <span className="font-mono text-[10px] text-slate-600">
                    Refreshed {formatOperatorTimestamp(lastRefreshedAtIso, timeDisplay)}
                  </span>
                ) : null}
                {tapeCapturedAt ? (
                  <span data-testid="header-tape-captured" className="font-mono text-[10px] text-slate-600">
                    Tape {formatOperatorTimestamp(tapeCapturedAt, timeDisplay)}
                  </span>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      </header>

      <div className={`mx-auto space-y-4 px-4 pt-6 sm:px-6 ${contentWide ? "max-w-[min(100%,92rem)]" : "max-w-6xl"}`}>
        {s ? (
          <section className={`${surfaceClass("")} overflow-hidden`} aria-labelledby="source-safety-heading">
            <div className="px-6 py-4 sm:px-8">
              <p id="source-safety-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
                Source &amp; safety
                <Tip text="Live Kraken tape vs synthetic demo, execution posture, and proof signals — no real-money orders in this build." />
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge label={s.paper_safe_execution ? "Paper-safe by default" : "Review execution mode"} tone={s.paper_safe_execution ? "emerald" : "amber"} />
                <Badge label={s.live_trading_enabled ? "Live trading enabled" : "Live trading disabled"} tone={s.live_trading_enabled ? "rose" : "slate"} />
                <Badge label={s.risk_router_active ? "Risk router active" : "Risk router idle"} tone={s.risk_router_active ? "emerald" : "slate"} />
                <Badge label={s.validation_artifacts_active ? "Validation artifacts on" : "Artifacts idle"} tone={s.validation_artifacts_active ? "emerald" : "slate"} />
              </div>
              <p className="mt-3 max-w-4xl text-xs leading-relaxed text-slate-600">{s.market_data_detail}</p>
            </div>
          </section>
        ) : null}

        <ProductModeSwitcher mode={productMode} onMode={onMode} />
        {children}
      </div>
    </>
  );
}

function scrollToId(id: string) {
  if (typeof document === "undefined") return;
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function ProductModeSwitcher({ mode, onMode }: { mode: ProductMode; onMode: (m: ProductMode) => void }) {
  return (
    <section
      data-testid="product-mode-switcher"
      className={`${surfaceClass("")} px-4 py-5 sm:px-8`}
      aria-label="Product mode"
    >
      <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">Mode</p>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        {PRODUCT_MODE_ORDER.map((m) => {
          const meta = MODE_META[m];
          return (
            <button
              type="button"
              key={m}
              onClick={() => {
                onMode(m);
                scrollToId(meta.anchor);
              }}
              className={`flex-1 rounded-xl px-4 py-3 text-left ring-1 transition ${
                mode === m ? "bg-white/[0.06] ring-teal-500/40" : "bg-white/[0.02] ring-white/[0.06] hover:bg-white/[0.04]"
              }`}
            >
              <p className="text-xs font-semibold text-white">{meta.label}</p>
              <p className="mt-1 text-[11px] leading-snug text-slate-500">{meta.purpose}</p>
              <p className="mt-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-600">Best for · {meta.bestFor}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
