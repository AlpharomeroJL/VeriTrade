import { formatOperatorTimestamp, type TimeDisplayMode } from "../../operatorTime";
import { surfaceClass } from "../uiPrimitives";
import { SectionHead } from "../SectionHead";
import { tapeSourceLabel } from "../tapeSource";

type TopMarketRow = {
  symbol: string;
  price: number;
  bid: number | null;
  ask: number | null;
  source: string;
  captured_at: string;
};

type OverviewLike = {
  top_markets?: TopMarketRow[] | null;
};

export function TopPairsStrip({ overview, timeDisplay }: { overview: OverviewLike | null; timeDisplay: TimeDisplayMode }) {
  return (
    <section className={surfaceClass("")} aria-label="Top pairs">
      <SectionHead eyebrow="Market context" title="Top pairs on tape" hint="Last ingested values for the default watchlist — freshness shown per row." />
      <div className="px-8 pb-10 pt-2">
        <p className="text-xs leading-relaxed text-slate-600">
          BTC/USD, ETH/USD, SOL/USD — Kraken mode pulls live public ticker when enabled; demo mode uses synthetic snapshots.
        </p>
        <div className="mt-6 space-y-3">
          {(overview?.top_markets?.length ?? 0) > 0 ? (
            overview!.top_markets!.map((row) => (
              <div
                key={row.symbol}
                className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-white/[0.03] px-4 py-3 ring-1 ring-white/[0.06]"
              >
                <span className="font-mono text-sm font-semibold text-white">{row.symbol.replace("USD", "/USD")}</span>
                <span
                  data-testid={`top-market-price-${row.symbol}`}
                  className="tabular-nums text-lg font-medium text-slate-100"
                >
                  {row.price.toLocaleString()}
                </span>
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
    </section>
  );
}
