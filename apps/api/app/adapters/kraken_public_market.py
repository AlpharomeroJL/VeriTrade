"""
Kraken market data adapter.

Modes:
- HTTPS public ticker (no credentials)
- External Kraken CLI (must be explicitly configured)

Execution / trading stays separate — this module is read-only market data.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"

# VeriTrade UI symbols -> Kraken REST pair parameter attempts (first match wins).
PAIR_ATTEMPTS: dict[str, list[str]] = {
    "BTCUSD": ["XBTUSD", "XXBTZUSD"],
    "ETHUSD": ["ETHUSD", "XETHZUSD"],
    "SOLUSD": ["SOLUSD"],
}

TOP_UI_SYMBOLS: tuple[str, ...] = ("BTCUSD", "ETHUSD", "SOLUSD")


@dataclass
class KrakenTickerRow:
    ui_symbol: str
    price: float
    bid: float | None
    ask: float | None
    kraken_pair_requested: str
    fetch_via: str  # kraken_cli | kraken_https


def _urllib_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "VeriTrade/1.0 (market data; read-only)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def _fetch_json_https(url: str) -> tuple[dict[str, Any], str]:
    raw = _urllib_get(url)
    return json.loads(raw.decode()), "kraken_https"


def _extract_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    if isinstance(v, list) and v:
        return _extract_float(v[0])
    return None


def _parse_ticker_payload(payload: dict[str, Any]) -> tuple[float, float | None, float | None]:
    err = payload.get("error") or []
    if err:
        raise RuntimeError(str(err))
    result = payload.get("result") or {}
    for _k, v in result.items():
        if not isinstance(v, dict):
            continue
        c = v.get("c") or []
        a = v.get("a") or []
        b = v.get("b") or []
        last = float(c[0]) if c else 0.0
        ask = float(a[0]) if a else None
        bid = float(b[0]) if b else None
        return last, bid, ask
    raise RuntimeError("empty_ticker_result")


def _parse_cli_payload(payload: dict[str, Any]) -> tuple[float, float | None, float | None]:
    # Accept several likely CLI schemas while remaining strict on price presence.
    if "error" in payload and payload.get("error"):
        raise RuntimeError(str(payload.get("error")))
    if "result" in payload and isinstance(payload["result"], dict):
        return _parse_ticker_payload(payload)
    # Native `kraken ticker -o json`: top-level pair key(s), e.g. {"XXBTZUSD": {"a":[],"b":[],"c":[]}}
    pair_blocks = {k: v for k, v in payload.items() if isinstance(v, dict) and k not in ("error", "result")}
    if pair_blocks:
        return _parse_ticker_payload({"error": [], "result": pair_blocks})

    last = _extract_float(payload.get("last")) or _extract_float(payload.get("price")) or _extract_float(payload.get("c"))
    bid = _extract_float(payload.get("bid")) or _extract_float(payload.get("b"))
    ask = _extract_float(payload.get("ask")) or _extract_float(payload.get("a"))
    if last is None:
        raise RuntimeError("cli_payload_missing_last")
    return last, bid, ask


def _volatility_from_spread(price: float, bid: float | None, ask: float | None) -> bool:
    if bid is None or ask is None or price <= 0:
        return False
    mid = (bid + ask) / 2.0
    if mid <= 0:
        return False
    spread_ratio = (ask - bid) / mid
    return spread_ratio > 0.012


def fetch_ticker_for_ui_symbol(ui_symbol: str) -> KrakenTickerRow:
    attempts = PAIR_ATTEMPTS.get(ui_symbol)
    if not attempts:
        raise ValueError(f"unsupported symbol {ui_symbol}")
    last_err: Exception | None = None
    for pair_param in attempts:
        url = f"{KRAKEN_TICKER_URL}?pair={pair_param}"
        try:
            payload, via = _fetch_json_https(url)
            price, bid, ask = _parse_ticker_payload(payload)
            return KrakenTickerRow(
                ui_symbol=ui_symbol,
                price=round(price, 2),
                bid=round(bid, 2) if bid is not None else None,
                ask=round(ask, 2) if ask is not None else None,
                kraken_pair_requested=pair_param,
                fetch_via=via,
            )
        except (RuntimeError, ValueError, urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            last_err = e
            continue
    raise RuntimeError(f"kraken_ticker_failed:{ui_symbol}:{last_err!s}")


def fetch_ticker_for_ui_symbol_cli(ui_symbol: str) -> KrakenTickerRow:
    attempts = PAIR_ATTEMPTS.get(ui_symbol)
    if not attempts:
        raise ValueError(f"unsupported symbol {ui_symbol}")
    s = get_settings()
    if not shutil.which(s.kraken_market_cli_bin):
        raise RuntimeError(f"kraken_cli_binary_not_found:{s.kraken_market_cli_bin}")
    template = (s.kraken_market_cli_ticker_template or "").strip()
    if not template:
        raise RuntimeError("kraken_cli_template_missing")

    last_err: Exception | None = None
    for pair_param in attempts:
        cmd = template.format(pair=pair_param, bin=s.kraken_market_cli_bin)
        try:
            raw = subprocess.check_output(
                cmd,
                shell=True,
                timeout=20,
                stderr=subprocess.STDOUT,
            )
            payload = json.loads(raw.decode())
            price, bid, ask = _parse_cli_payload(payload)
            return KrakenTickerRow(
                ui_symbol=ui_symbol,
                price=round(price, 2),
                bid=round(bid, 2) if bid is not None else None,
                ask=round(ask, 2) if ask is not None else None,
                kraken_pair_requested=pair_param,
                fetch_via="kraken_cli",
            )
        except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
            last_err = e
            continue
    raise RuntimeError(f"kraken_cli_ticker_failed:{ui_symbol}:{last_err!s}")


def fetch_top_market_rows() -> list[KrakenTickerRow]:
    out: list[KrakenTickerRow] = []
    for sym in TOP_UI_SYMBOLS:
        out.append(fetch_ticker_for_ui_symbol(sym))
    return out


def fetch_ohlc(ui_symbol: str, *, interval_minutes: int = 1, max_bars: int = 720) -> tuple[list[dict[str, Any]], str]:
    """Kraken public OHLC. interval_minutes must be one of 1, 5, 15, 30, 60 (Kraken API). Returns bars oldest-first."""
    if interval_minutes not in (1, 5, 15, 30, 60):
        raise ValueError(f"unsupported ohlc interval {interval_minutes}")
    attempts = PAIR_ATTEMPTS.get(ui_symbol)
    if not attempts:
        raise ValueError(f"unsupported symbol {ui_symbol}")
    cap = max(10, min(720, int(max_bars)))
    last_err: Exception | None = None
    for pair_param in attempts:
        url = f"{KRAKEN_OHLC_URL}?pair={pair_param}&interval={interval_minutes}"
        try:
            payload, via = _fetch_json_https(url)
            err = payload.get("error") or []
            if err:
                raise RuntimeError(str(err))
            result = payload.get("result") or {}
            series: list[list[Any]] | None = None
            for _k, v in result.items():
                if _k == "last" or not isinstance(v, list):
                    continue
                series = v
                break
            if not series:
                raise RuntimeError("empty_ohlc_result")
            tail = series[-cap:]
            out: list[dict[str, Any]] = []
            for row in tail:
                if not isinstance(row, list) or len(row) < 5:
                    continue
                ts = int(row[0])
                ot = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
                o, h, low, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
                vol = float(row[6]) if len(row) > 6 else 0.0
                out.append(
                    {
                        "open_time": ot,
                        "o": round(o, 6),
                        "h": round(h, 6),
                        "l": round(low, 6),
                        "c": round(c, 6),
                        "volume": vol,
                    }
                )
            return out, via
        except (RuntimeError, ValueError, urllib.error.URLError, OSError, json.JSONDecodeError, TypeError) as e:
            last_err = e
            continue
    raise RuntimeError(f"kraken_ohlc_failed:{ui_symbol}:{last_err!s}")


def fetch_ohlc_1m(ui_symbol: str, *, max_bars: int = 720) -> tuple[list[dict[str, Any]], str]:
    """Backward-compatible alias for 1-minute OHLC."""
    return fetch_ohlc(ui_symbol, interval_minutes=1, max_bars=max_bars)
