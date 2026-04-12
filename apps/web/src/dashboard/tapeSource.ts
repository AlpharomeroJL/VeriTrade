export function tapeSourceLabel(source: string | undefined): string {
  if (!source) return "—";
  if (source === "mock") return "Demo snapshot (synthetic)";
  if (source === "mock_fallback") return "Demo fallback (Kraken unreachable)";
  if (source === "mock_fallback_cli_unavailable") return "Demo fallback (Kraken CLI unavailable)";
  if (source === "kraken_cli") return "Kraken CLI ticker";
  if (source === "kraken_https") return "Kraken public ticker (HTTPS)";
  const km = source.match(/^kraken_(https|cli)_ohlc_(\d+)m$/);
  if (km) return `Kraken public ${km[2]}-minute OHLC (${km[1]})`;
  if (source === "kraken_https_ohlc" || source === "kraken_cli_ohlc") return "Kraken public 1-minute OHLC";
  if (source.startsWith("snapshot_1m_aggregate_")) {
    const m = source.match(/_(\d+)m$/);
    return m ? `Demo 1m bars rolled up to ${m[1]}-minute candles` : "Demo tape rolled up for chart timeframe";
  }
  if (source.startsWith("candle_cache_")) {
    const m = source.match(/candle_cache_(\d+)m$/);
    return m ? `Cached 1m data shown as ${m[1]}-minute candles` : "Cached candles (aggregated)";
  }
  if (source === "snapshot_1m_aggregate") return "Demo tape rolled into 1-minute bars";
  return source;
}
