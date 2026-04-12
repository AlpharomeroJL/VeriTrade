/** Operator OHLC chart — TradingView Lightweight Charts (zoom, pan, crosshair tooltip, timeframes). */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  createChart,
  CrosshairMode,
  type AutoscaleInfoProvider,
  type ISeriesApi,
  type SeriesMarker,
  type UTCTimestamp,
} from "lightweight-charts";
import { formatChartAxisTime, formatOperatorTimestamp, type TimeDisplayMode } from "./operatorTime";

export type Candle = { t: string; o: number; h: number; l: number; c: number; v?: number; forming?: boolean };
export type ChartMarker = { ts: string; price: number; kind: string; label: string };

export type ChartIntervalId = "1m" | "5m" | "15m" | "30m" | "1h";

const INTERVALS: ChartIntervalId[] = ["1m", "5m", "15m", "30m", "1h"];

function utcSec(c: Candle): UTCTimestamp {
  return Math.floor(new Date(c.t).getTime() / 1000) as UTCTimestamp;
}

function alignMarkerToBar(markerMs: number, barSecSorted: number[]): UTCTimestamp {
  const ts = Math.floor(markerMs / 1000);
  if (!barSecSorted.length) return ts as UTCTimestamp;
  let lo = 0;
  let hi = barSecSorted.length - 1;
  let ans = barSecSorted[0]!;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (barSecSorted[mid]! <= ts) {
      ans = barSecSorted[mid]!;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans as UTCTimestamp;
}

const MARKER_STYLES: Record<
  string,
  { color: string; position: SeriesMarker<UTCTimestamp>["position"]; shape: SeriesMarker<UTCTimestamp>["shape"] }
> = {
  buy: { color: "#34d399", position: "belowBar", shape: "arrowUp" },
  sell: { color: "#38bdf8", position: "aboveBar", shape: "arrowDown" },
  blocked: { color: "#fb7185", position: "aboveBar", shape: "circle" },
  reduced: { color: "#fbbf24", position: "inBar", shape: "circle" },
  review: { color: "#a78bfa", position: "aboveBar", shape: "square" },
};

function priceFormatForSymbol(sym: string) {
  const upper = sym.toUpperCase();
  if (upper.startsWith("BTC") || upper.startsWith("ETH")) {
    return { type: "price" as const, precision: 2, minMove: 0.01 };
  }
  return { type: "price" as const, precision: 4, minMove: 0.0001 };
}

/** When 1m OHLC span is tiny vs price, pad autoscale so bodies/wicks are not crushed to a hairline. */
function candleAutoscaleInfoProvider(is1m: boolean): AutoscaleInfoProvider {
  return (original) => {
    const res = original();
    if (res === null) return res;
    const minV = res.priceRange.minValue;
    const maxV = res.priceRange.maxValue;
    const span = Math.max(maxV - minV, Number.EPSILON);
    const mid = (minV + maxV) / 2;
    const absMid = Math.abs(mid) > 1e-12 ? Math.abs(mid) : Math.max(Math.abs(minV), Math.abs(maxV), 1);
    const relSpan = span / absMid;
    const tight = is1m ? relSpan < 0.00035 : relSpan < 0.00012;
    if (!tight) {
      return is1m ? { ...res, margins: { above: 10, below: 10 } } : res;
    }
    const minRel = is1m ? 0.00042 : 0.00018;
    const minSpan = absMid * minRel;
    const pad = Math.max((minSpan - span) / 2, absMid * 0.00002);
    return {
      priceRange: { minValue: minV - pad, maxValue: maxV + pad },
      margins: is1m ? { above: 18, below: 18 } : { above: 10, below: 10 },
    };
  };
}

export function LiveCandleChart({
  symbol,
  candles,
  markers: tradeMarkers,
  positionNotional,
  sourceHint,
  maShort,
  maLong,
  interval,
  timeDisplay,
  onIntervalChange,
  onTimeDisplayChange,
  density = "default",
}: {
  symbol: string;
  candles: Candle[];
  markers: ChartMarker[];
  positionNotional: number | null | undefined;
  sourceHint?: string;
  maShort?: number | null;
  maLong?: number | null;
  interval: ChartIntervalId;
  timeDisplay: TimeDisplayMode;
  onIntervalChange?: (iv: ChartIntervalId) => void;
  onTimeDisplayChange?: (m: TimeDisplayMode) => void;
  density?: "default" | "workstation";
}) {
  const workstation = density === "workstation";
  const timeDisplayRef = useRef(timeDisplay);
  timeDisplayRef.current = timeDisplay;

  const wrapRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const maFastRef = useRef<ISeriesApi<"Line"> | null>(null);
  const maSlowRef = useRef<ISeriesApi<"Line"> | null>(null);
  const candleByTimeRef = useRef<Map<number, Candle>>(new Map());
  const lastFitKeyRef = useRef("");
  const [tip, setTip] = useState<{
    x: number;
    y: number;
    timeStr: string;
    o: number;
    h: number;
    l: number;
    c: number;
    vol: number | null;
    forming: boolean;
  } | null>(null);

  const barSecSorted = useMemo(() => {
    const s = candles.map((c) => Math.floor(new Date(c.t).getTime() / 1000));
    return [...new Set(s)].sort((a, b) => a - b);
  }, [candles]);

  const lastClose = candles.length ? candles[candles.length - 1]?.c : undefined;
  const posLabel =
    positionNotional != null && !Number.isNaN(positionNotional)
      ? positionNotional > 0
        ? `Paper position ≈ ${new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(positionNotional)} exposure`
        : "Flat — no open paper position"
      : "Position updates after governed cycles";

  const initChart = useCallback(() => {
    const wrap = wrapRef.current;
    if (!wrap) return () => {};
    const rect = wrap.getBoundingClientRect();
    const w = Math.max(280, Math.floor(rect.width));
    const is1m = interval === "1m";
    const tall = density === "workstation";
    const chartHeight = tall ? (is1m ? 560 : 520) : is1m ? 468 : 420;

    const chart = createChart(wrap, {
      width: w,
      height: chartHeight,
      layout: {
        background: { type: ColorType.Solid, color: "#0a0d14" },
        textColor: "#94a3b8",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(148,163,184,0.06)" },
        horzLines: { color: "rgba(148,163,184,0.06)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: {
        borderVisible: false,
        autoScale: true,
        scaleMargins: is1m ? { top: 0.03, bottom: 0.03 } : { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
        rightOffset: is1m ? 6 : 4,
        barSpacing: is1m ? 11 : 8,
        minBarSpacing: is1m ? 4 : 2,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      localization: {
        locale: "en-GB",
        timeFormatter: (t: number) => {
          const sec = typeof t === "number" ? t : 0;
          return formatChartAxisTime(sec, timeDisplayRef.current, interval === "1h");
        },
      },
    });

    const candle = chart.addCandlestickSeries({
      upColor: is1m ? "rgba(52,211,153,0.95)" : "rgba(45,212,191,0.9)",
      downColor: is1m ? "rgba(251,113,133,0.96)" : "rgba(248,113,113,0.92)",
      borderVisible: true,
      borderUpColor: is1m ? "#0d9488" : "#0f766e",
      borderDownColor: is1m ? "#e11d48" : "#dc2626",
      wickVisible: true,
      wickUpColor: is1m ? "rgba(226,232,240,0.95)" : "rgb(148,163,184)",
      wickDownColor: is1m ? "rgba(226,232,240,0.95)" : "rgb(148,163,184)",
      priceFormat: priceFormatForSymbol(symbol),
      autoscaleInfoProvider: candleAutoscaleInfoProvider(is1m),
    });
    const maF = chart.addLineSeries({
      color: is1m ? "rgba(45,212,191,0.22)" : "rgba(45,212,191,0.45)",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      lineStyle: 2,
    });
    const maS = chart.addLineSeries({
      color: is1m ? "rgba(56,189,248,0.2)" : "rgba(56,189,248,0.42)",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      lineStyle: 2,
    });

    chart.subscribeCrosshairMove((param) => {
      if (!param.point || param.point.x < 0 || param.point.y < 0) {
        setTip(null);
        return;
      }
      const t = param.time;
      if (t === undefined || t === null) {
        setTip(null);
        return;
      }
      const sec = typeof t === "number" ? t : 0;
      const c = candleByTimeRef.current.get(sec);
      if (!c) {
        setTip(null);
        return;
      }
      const vol = c.v != null && !Number.isNaN(c.v) ? c.v : null;
      const timeStr = formatOperatorTimestamp(typeof c.t === "string" ? c.t : String(c.t), timeDisplayRef.current);
      setTip({
        x: param.point.x,
        y: param.point.y,
        timeStr,
        o: c.o,
        h: c.h,
        l: c.l,
        c: c.c,
        vol: vol != null && vol > 0 ? vol : null,
        forming: Boolean(c.forming),
      });
    });

    chartRef.current = chart;
    seriesRef.current = candle;
    maFastRef.current = maF;
    maSlowRef.current = maS;

    const ro = new ResizeObserver(() => {
      if (!wrapRef.current || !chartRef.current) return;
      chartRef.current.applyOptions({ width: Math.max(280, Math.floor(wrapRef.current.getBoundingClientRect().width)) });
    });
    ro.observe(wrap);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      maFastRef.current = null;
      maSlowRef.current = null;
      lastFitKeyRef.current = "";
    };
  }, [interval, symbol]);

  useEffect(() => {
    return initChart();
  }, [initChart]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.applyOptions({
      localization: {
        locale: "en-GB",
        timeFormatter: (t: number) => {
          const sec = typeof t === "number" ? t : 0;
          return formatChartAxisTime(sec, timeDisplay, interval === "1h");
        },
      },
    });
  }, [timeDisplay, interval]);

  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    const maF = maFastRef.current;
    const maS = maSlowRef.current;
    if (!chart || !series || !maF || !maS) return;

    const map = new Map<number, Candle>();
    const data = candles.map((c) => {
      const t = utcSec(c);
      map.set(Number(t), c);
      return {
        time: t,
        open: c.o,
        high: c.h,
        low: c.l,
        close: c.c,
      };
    });
    candleByTimeRef.current = map;
    series.setData(data);

    const mkSize = interval === "1m" ? 0.85 : 1.05;
    const seriesMarkers: SeriesMarker<UTCTimestamp>[] = tradeMarkers.map((m) => {
      const st = MARKER_STYLES[m.kind] ?? MARKER_STYLES.review!;
      const raw = new Date(m.ts).getTime();
      const t = alignMarkerToBar(raw, barSecSorted);
      const ch = m.kind.charAt(0).toUpperCase();
      return { time: t, position: st.position, color: st.color, shape: st.shape, text: ch, size: mkSize };
    });
    series.setMarkers(seriesMarkers);

    if (maShort != null && maLong != null && data.length) {
      const lineT = data.map((d) => d.time);
      maF.setData(lineT.map((tm) => ({ time: tm, value: maShort })));
      maS.setData(lineT.map((tm) => ({ time: tm, value: maLong })));
    } else {
      maF.setData([]);
      maS.setData([]);
    }

    const fitKey = `${symbol}|${interval}`;
    if (data.length && lastFitKeyRef.current !== fitKey) {
      chart.timeScale().fitContent();
      lastFitKeyRef.current = fitKey;
    }
  }, [candles, tradeMarkers, barSecSorted, interval, symbol, maShort, maLong]);

  if (candles.length < 2) {
    return (
      <div className="rounded-xl bg-black/30 px-6 py-12 text-center text-sm text-slate-500 ring-1 ring-white/[0.06]">
        <p className="font-medium text-slate-400">Loading candles…</p>
        <p className="mt-2 max-w-md mx-auto text-xs leading-relaxed">
          Chart data loads from the API (Kraken OHLC when enabled, otherwise demo tape). If this persists, run a demo cycle or check the API.
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${workstation ? "flex min-h-0 flex-col" : ""}`}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className={`font-mono font-semibold tracking-tight text-white ${workstation ? "text-xl" : "text-lg"}`}>{symbol}</p>
          <p className="mt-0.5 text-xs text-slate-500">{sourceHint ?? "OHLC"}</p>
          {lastClose != null ? (
            <p
              data-testid="chart-last-close"
              className={`mt-1 font-semibold tabular-nums text-teal-200/95 ${workstation ? "text-3xl sm:text-4xl" : "text-2xl"}`}
            >
              {lastClose.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </p>
          ) : null}
          {maShort != null && maLong != null ? (
            <p className="mt-1 text-[11px] text-slate-600">
              Avg(10) <span className="font-mono text-slate-400">{maShort.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
              {" · "}
              Avg(50) <span className="font-mono text-slate-400">{maLong.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
            </p>
          ) : null}
        </div>
        <p className={`text-right text-[11px] leading-snug text-slate-500 ${workstation ? "max-w-[14rem]" : "max-w-xs"}`}>{posLabel}</p>
      </div>

      {onIntervalChange || onTimeDisplayChange ? (
        <div className="flex flex-wrap items-center justify-between gap-4">
          {onIntervalChange ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Timeframe</span>
              <div className="inline-flex flex-wrap gap-1 rounded-lg bg-black/35 p-1 ring-1 ring-white/[0.06]">
                {INTERVALS.map((iv) => (
                  <button
                    key={iv}
                    type="button"
                    onClick={() => onIntervalChange(iv)}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
                      interval === iv ? "bg-teal-500/20 text-teal-100 ring-1 ring-teal-500/35" : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
                    }`}
                  >
                    {iv}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <span />
          )}
          {onTimeDisplayChange ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Clock</span>
              <div className="inline-flex gap-1 rounded-lg bg-black/35 p-1 ring-1 ring-white/[0.06]">
                <button
                  type="button"
                  onClick={() => onTimeDisplayChange("local")}
                  className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
                    timeDisplay === "local"
                      ? "bg-sky-500/20 text-sky-100 ring-1 ring-sky-500/35"
                      : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
                  }`}
                >
                  Local
                </button>
                <button
                  type="button"
                  onClick={() => onTimeDisplayChange("utc")}
                  className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
                    timeDisplay === "utc"
                      ? "bg-sky-500/20 text-sky-100 ring-1 ring-sky-500/35"
                      : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
                  }`}
                >
                  UTC
                </button>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="relative w-full rounded-xl bg-black/40 ring-1 ring-white/[0.06]">
        <div ref={wrapRef} className={`vt-chart-host w-full ${interval === "1m" ? "min-h-[468px]" : "min-h-[420px]"}`} />
        {tip ? (
          <div
            className="pointer-events-none absolute z-20 min-w-[10rem] max-w-[16rem] rounded-lg border border-white/[0.08] bg-[#0f141c]/95 px-3 py-2 text-[11px] text-slate-300 shadow-xl backdrop-blur-sm"
            style={{
              left: Math.min(Math.max(tip.x + 12, 8), (wrapRef.current?.clientWidth ?? 400) - 180),
              top: Math.max(tip.y - 8, 8),
            }}
          >
            <div className="font-semibold text-slate-100">{tip.timeStr}</div>
            <div className="mt-1.5 space-y-0.5 font-mono tabular-nums text-slate-400">
              <div>O {tip.o.toLocaleString(undefined, { maximumFractionDigits: 6 })}</div>
              <div>H {tip.h.toLocaleString(undefined, { maximumFractionDigits: 6 })}</div>
              <div>L {tip.l.toLocaleString(undefined, { maximumFractionDigits: 6 })}</div>
              <div>C {tip.c.toLocaleString(undefined, { maximumFractionDigits: 6 })}</div>
              {tip.vol != null ? <div>Vol {tip.vol.toLocaleString(undefined, { maximumFractionDigits: 4 })}</div> : null}
              {tip.forming ? <div className="text-amber-200/90">Forming bar (live minute)</div> : null}
            </div>
          </div>
        ) : null}
      </div>

      <p className={`text-slate-600 ${workstation ? "text-[9px] leading-snug" : "text-[10px]"}`}>
        {workstation
          ? "Scroll zoom · drag pan · double-click price axis resets. Tape polls ~1s in paper/watch."
          : "Scroll wheel zoom · click-drag pan · double-click price axis resets scale. In Paper / Watch modes the tape and chart poll automatically (~1s). Markers: paper fills, blocks, trims, review."}
      </p>

      <div className={`flex flex-wrap gap-x-4 gap-y-2 text-slate-500 ${workstation ? "text-[9px]" : "text-[10px]"}`}>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-2 rounded-sm bg-teal-400/90 ring-1 ring-teal-600/50" /> Up bar
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-2 rounded-sm bg-rose-400/90 ring-1 ring-rose-600/50" /> Down bar
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-400" /> Buy
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-sky-400" /> Sell
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-rose-400" /> Blocked
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-amber-400" /> Reduced
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-violet-400" /> Review
        </span>
      </div>
    </div>
  );
}
