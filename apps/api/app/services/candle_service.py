"""1-minute OHLC persistence for charts and strategy warm-up (read-only Kraken public OHLC)."""

from __future__ import annotations

import calendar
import statistics
import time
from collections import defaultdict
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.adapters.kraken_public_market import TOP_UI_SYMBOLS, fetch_ohlc, fetch_ohlc_1m
from app.config import get_settings as get_app_settings
from app.models import MarketCandle, MarketSnapshot

_KRAKEN_OHLC_LAST_FETCH: dict[str, float] = {}
_OHLC_THROTTLE_SEC = 55.0


def _upsert_bars(db: Session, symbol: str, bars: list[dict], *, source: str, interval_minutes: int = 1) -> None:
    sym = symbol.upper()
    for b in bars:
        ot = b["open_time"]
        if isinstance(ot, datetime) and ot.tzinfo is not None:
            ot = ot.replace(tzinfo=None)
        q = select(MarketCandle).where(
            MarketCandle.symbol == sym,
            MarketCandle.interval_minutes == interval_minutes,
            MarketCandle.open_time == ot,
        )
        row = db.execute(q).scalar_one_or_none()
        if row is None:
            row = MarketCandle(
                symbol=sym,
                interval_minutes=interval_minutes,
                open_time=ot,
                open_price=float(b["o"]),
                high=float(b["h"]),
                low=float(b["l"]),
                close=float(b["c"]),
                volume=float(b.get("volume", 0.0)),
                source=source,
            )
            db.add(row)
        else:
            row.open_price = float(b["o"])
            row.high = float(b["h"])
            row.low = float(b["l"])
            row.close = float(b["c"])
            row.volume = float(b.get("volume", 0.0))
            row.source = source
    db.commit()


def _bars_from_snapshots(db: Session, symbol: str, max_bars: int) -> list[dict]:
    sym = symbol.upper()
    lim = max(200, min(8000, max_bars * 30))
    q = (
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == sym)
        .order_by(desc(MarketSnapshot.captured_at))
        .limit(lim)
    )
    rows = list(db.execute(q).scalars().all())
    buckets: dict[datetime, list[float]] = defaultdict(list)
    for r in rows:
        cap = r.captured_at
        if cap.tzinfo is not None:
            cap = cap.replace(tzinfo=None)
        m = cap.replace(second=0, microsecond=0)
        buckets[m].append(float(r.price))
    keys = sorted(buckets.keys(), reverse=True)[:max_bars]
    keys.sort()
    out: list[dict] = []
    for m in keys:
        px = buckets[m]
        o, h, low, c = px[-1], max(px), min(px), px[0]
        out.append({"open_time": m, "o": o, "h": h, "l": low, "c": c, "volume": 0.0})
    return out


def refresh_candles_for_symbol(db: Session, symbol: str, *, target_bars: int = 480, force_network: bool = False) -> str:
    """
    Backfill / refresh 1m candles for strategy + chart. Returns source label for diagnostics.
    Kraken OHLC is throttled per symbol so 3s UI polls do not hammer the public API.
    """
    sym = symbol.upper()
    want = max(240, min(720, int(target_bars)))
    source = "unchanged"
    now_m = time.monotonic()
    stale_net = force_network or (now_m - _KRAKEN_OHLC_LAST_FETCH.get(sym, 0.0) >= _OHLC_THROTTLE_SEC)

    n_rows = int(
        db.scalar(
            select(func.count())
            .select_from(MarketCandle)
            .where(MarketCandle.symbol == sym, MarketCandle.interval_minutes == 1)
        )
        or 0
    )

    settings = get_app_settings()
    tape_mode = (settings.market_data_mode or "demo").lower()
    use_kraken_ohlc = tape_mode in ("kraken_public", "kraken_cli")

    if sym in TOP_UI_SYMBOLS and use_kraken_ohlc and stale_net and (force_network or n_rows < 120):
        try:
            bars, via = fetch_ohlc_1m(sym, max_bars=want)
            if bars:
                _upsert_bars(db, sym, bars, source=f"{via}_ohlc")
                source = via
            _KRAKEN_OHLC_LAST_FETCH[sym] = now_m
        except Exception:
            pass

    if n_rows < 80 or (sym not in TOP_UI_SYMBOLS and n_rows < 120):
        agg = _bars_from_snapshots(db, sym, want)
        if agg:
            _upsert_bars(db, sym, agg, source="snapshot_1m_aggregate")
            if source == "unchanged":
                source = "snapshot_1m_aggregate"

    return source


def load_candles_asc(db: Session, symbol: str, limit: int) -> list[MarketCandle]:
    sym = symbol.upper()
    lim = max(30, min(720, limit))
    q = (
        select(MarketCandle)
        .where(MarketCandle.symbol == sym, MarketCandle.interval_minutes == 1)
        .order_by(desc(MarketCandle.open_time))
        .limit(lim)
    )
    rows = list(db.execute(q).scalars().all())
    rows.reverse()
    return rows


def load_candles_1m_asc_many(db: Session, symbol: str, limit: int) -> list[MarketCandle]:
    """Load more 1m history for higher-TF aggregation (demo / non-Kraken paths)."""
    sym = symbol.upper()
    lim = max(120, min(4000, limit))
    q = (
        select(MarketCandle)
        .where(MarketCandle.symbol == sym, MarketCandle.interval_minutes == 1)
        .order_by(desc(MarketCandle.open_time))
        .limit(lim)
    )
    rows = list(db.execute(q).scalars().all())
    rows.reverse()
    return rows


def _utc_ts_naive(dt: datetime) -> int:
    """Treat naive DB datetimes as UTC (matches Kraken OHLC ingestion)."""
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return calendar.timegm(dt.timetuple())


def _bucket_open_time_naive_utc(dt: datetime, interval_minutes: int) -> datetime:
    sec = interval_minutes * 60
    floored = (_utc_ts_naive(dt) // sec) * sec
    return datetime.utcfromtimestamp(floored)


def aggregate_1m_dicts_to_interval(asc: list[dict], interval_minutes: int) -> list[dict]:
    """Merge ascending 1m OHLC dicts (t,o,h,l,c,v,forming) into higher intervals. Drops forming rows."""
    if interval_minutes <= 1:
        return asc
    closed = [c for c in asc if not c.get("forming")]
    if not closed:
        return []
    buckets: dict[datetime, dict] = {}
    for c in closed:
        t = c["t"]
        if isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00"))
            if t.tzinfo:
                t = t.replace(tzinfo=None)
        ot = _bucket_open_time_naive_utc(t, interval_minutes)
        o, h, low, cl, v = float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"]), float(c.get("v", 0.0))
        if ot not in buckets:
            buckets[ot] = {"t": ot, "o": o, "h": h, "l": low, "c": cl, "v": v, "forming": False}
        else:
            b = buckets[ot]
            b["h"] = max(float(b["h"]), h)
            b["l"] = min(float(b["l"]), low)
            b["c"] = cl
            b["v"] = float(b.get("v", 0.0)) + v
    out = [buckets[k] for k in sorted(buckets.keys())]
    return out


def _forming_bar_for_current_minute(db: Session, symbol: str, last_closed_open: datetime | None) -> dict | None:
    """In-progress 1m bar from ingested snapshots (Kraken ticker / demo tape) for the current clock minute."""
    sym = symbol.upper()
    cur = datetime.utcnow().replace(second=0, microsecond=0)
    minute_start = cur
    if last_closed_open is not None and last_closed_open >= cur:
        minute_start = last_closed_open
    q = (
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == sym, MarketSnapshot.captured_at >= minute_start)
        .order_by(MarketSnapshot.captured_at.asc())
    )
    snaps = list(db.execute(q).scalars().all())
    if not snaps:
        return None
    prices = [float(s.price) for s in snaps]
    return {
        "open_time": minute_start,
        "o": prices[0],
        "h": max(prices),
        "l": min(prices),
        "c": prices[-1],
        "v": 0.0,
        "forming": True,
    }


def _merge_forming(base: list[dict], forming: dict | None) -> None:
    if not forming:
        return
    ft = forming["open_time"]
    if not base or ft > base[-1]["t"]:
        base.append(
            {
                "t": forming["open_time"],
                "o": forming["o"],
                "h": forming["h"],
                "l": forming["l"],
                "c": forming["c"],
                "v": 0.0,
                "forming": True,
            }
        )
        return
    if base and ft == base[-1]["t"]:
        last = base[-1]
        base[-1] = {
            "t": ft,
            "o": last["o"],
            "h": max(float(last["h"]), forming["h"]),
            "l": min(float(last["l"]), forming["l"]),
            "c": forming["c"],
            "v": float(last.get("v", 0)),
            "forming": True,
        }


def candles_for_chart_pack(
    db: Session, symbol: str, limit: int, *, interval_minutes: int = 1
) -> tuple[list[dict], list[dict], str]:
    """OHLC for chart: 1m from DB + forming bar; higher TF from Kraken OHLC or 1m aggregation."""
    sym = symbol.upper()
    lim = max(30, min(720, int(limit)))
    settings = get_app_settings()
    tape_mode = (settings.market_data_mode or "demo").lower()
    use_kraken = tape_mode in ("kraken_public", "kraken_cli")

    if interval_minutes <= 1:
        src = refresh_candles_for_symbol(db, sym, target_bars=max(lim, 480))
        closed = load_candles_asc(db, sym, lim)
        if src == "unchanged" and closed:
            src = closed[-1].source or "candle_cache"
        last_ot = closed[-1].open_time if closed else None
        base = [
            {
                "t": r.open_time,
                "o": float(r.open_price),
                "h": float(r.high),
                "l": float(r.low),
                "c": float(r.close),
                "v": float(r.volume),
                "forming": False,
            }
            for r in closed
        ]
        forming = _forming_bar_for_current_minute(db, sym, last_ot)
        _merge_forming(base, forming)
        points = [{"t": c["t"], "price": c["c"]} for c in base]
        return base, points, src

    if sym in TOP_UI_SYMBOLS and use_kraken:
        try:
            bars, via = fetch_ohlc(sym, interval_minutes=interval_minutes, max_bars=lim)
            base = [
                {
                    "t": b["open_time"],
                    "o": float(b["o"]),
                    "h": float(b["h"]),
                    "l": float(b["l"]),
                    "c": float(b["c"]),
                    "v": float(b.get("volume", 0.0)),
                    "forming": False,
                }
                for b in bars
            ]
            points = [{"t": c["t"], "price": c["c"]} for c in base]
            return base, points, f"{via}_ohlc_{interval_minutes}m"
        except Exception:
            pass

    need_1m = min(4000, max(lim * interval_minutes * 3, 720))
    src = refresh_candles_for_symbol(db, sym, target_bars=max(480, min(need_1m, 720)))
    closed_1m = load_candles_1m_asc_many(db, sym, need_1m)
    if src == "unchanged" and closed_1m:
        src = closed_1m[-1].source or "candle_cache"
    last_ot = closed_1m[-1].open_time if closed_1m else None
    base_1m = [
        {
            "t": r.open_time,
            "o": float(r.open_price),
            "h": float(r.high),
            "l": float(r.low),
            "c": float(r.close),
            "v": float(r.volume),
            "forming": False,
        }
        for r in closed_1m
    ]
    forming = _forming_bar_for_current_minute(db, sym, last_ot)
    _merge_forming(base_1m, forming)
    agg = aggregate_1m_dicts_to_interval(base_1m, interval_minutes)
    agg = agg[-lim:] if len(agg) > lim else agg
    if not agg and base_1m:
        agg = aggregate_1m_dicts_to_interval([c for c in base_1m if not c.get("forming")], interval_minutes)[-lim:]
    points = [{"t": c["t"], "price": c["c"]} for c in agg]
    if "snapshot" in src or "aggregate" in src:
        out_src = f"snapshot_1m_aggregate_{interval_minutes}m"
    elif src == "unchanged":
        out_src = f"candle_cache_{interval_minutes}m"
    else:
        out_src = f"{src}_{interval_minutes}m"
    return agg, points, out_src


def recent_close_prices(db: Session, symbol: str, n: int = 60) -> list[float]:
    rows = load_candles_asc(db, symbol, n)
    return [float(r.close) for r in rows]


def _human_chart_data_lineage(source_hint: str, interval_minutes: int) -> str:
    """Plain-language chart provenance (no raw source keys in operator copy)."""
    s = (source_hint or "").lower()
    if "kraken" in s and interval_minutes <= 1:
        return (
            "These bars use recent Kraken public one-minute OHLC kept for this session; "
            "live public ticker snapshots align the latest print with the chart."
        )
    if "kraken" in s and interval_minutes > 1:
        return (
            "These bars are Kraken public OHLC at this bar width when available; otherwise one-minute Kraken "
            "history is rolled up to match the timeframe you selected. Ticker context still anchors the latest price."
        )
    if "snapshot" in s or "aggregate" in s:
        return "Demo mode rolls ingested snapshots into these bars for safe rehearsal (no venue orders from the chart)."
    if "candle_cache" in s:
        return "One-minute history stored here is aggregated to this timeframe for display."
    return "OHLC history stored for this symbol in the session feeds the bars you see."


def build_market_context_dict(
    candles: list[dict], *, source_hint: str, interval_minutes: int = 1
) -> dict | None:
    closed = [c for c in candles if not c.get("forming")]
    if len(closed) < 5:
        closed = candles
    if len(closed) < 5:
        return None
    closes = [float(c["c"]) for c in closed]
    highs = [float(c["h"]) for c in closed]
    lows = [float(c["l"]) for c in closed]
    n = len(closes)

    bar_label = "hourly" if interval_minutes >= 60 else "1-minute" if interval_minutes == 1 else f"{interval_minutes}-minute"

    w10 = min(10, n)
    w20 = min(20, n)
    w50 = min(50, n)
    ma_short = sum(closes[-w10:]) / w10
    ma_long = sum(closes[-w50:]) / w50

    if ma_short > ma_long * 1.0008:
        trend_key, trend_plain = (
            "up",
            f"The last stretch of {bar_label} prices has mostly drifted upward.",
        )
    elif ma_short < ma_long * 0.9992:
        trend_key, trend_plain = (
            "down",
            f"The last stretch of {bar_label} prices has mostly drifted downward.",
        )
    else:
        trend_key, trend_plain = (
            "sideways",
            "Prices have been going back and forth without a strong one-way move.",
        )

    if n > 11 and closes[-12] != 0:
        mom_pct = (closes[-1] - closes[-12]) / abs(closes[-12]) * 100.0
    else:
        mom_pct = 0.0
    if mom_pct > 0.15:
        mom_plain = f"Short-term momentum is positive (about {mom_pct:+.2f}% over the last ~10 minutes)."
    elif mom_pct < -0.15:
        mom_plain = f"Short-term momentum is negative (about {mom_pct:+.2f}% over the last ~10 minutes)."
    else:
        mom_plain = "Momentum is fairly flat — no strong push up or down in the last few bars."

    rets: list[float] = []
    for i in range(max(1, n - w20), n):
        if closes[i - 1]:
            rets.append((closes[i] - closes[i - 1]) / abs(closes[i - 1]))
    std = statistics.pstdev(rets) if len(rets) > 1 else 0.0
    if std < 0.0008:
        vol_key, vol_plain = "calm", "Volatility looks calm — bar-to-bar wiggles are small."
    elif std < 0.0025:
        vol_key, vol_plain = "normal", f"Volatility looks normal for these {bar_label} bars."
    else:
        vol_key, vol_plain = "elevated", "Volatility looks elevated — prices are jumping more bar-to-bar."

    rng = max(highs[-w20:]) - min(lows[-w20:])
    mid = (max(highs[-w20:]) + min(lows[-w20:])) / 2.0 if w20 else closes[-1]
    band_pct = (rng / mid * 100.0) if mid else 0.0

    if interval_minutes >= 60:
        count_line = f"The chart summarizes the last {n} hourly OHLC bars for the timeframe you selected."
    else:
        count_line = f"The chart summarizes the last {n} {bar_label} OHLC bars for the timeframe you selected."
    lineage_line = _human_chart_data_lineage(source_hint, interval_minutes)

    saw_lines = [
        trend_plain,
        mom_plain,
        vol_plain,
        count_line,
        lineage_line,
        f"Rough 20-bar range is about {band_pct:.2f}% of price — that helps the bot judge how noisy the tape is.",
    ]

    return {
        "trend": trend_key,
        "momentum": "positive" if mom_pct > 0.08 else "negative" if mom_pct < -0.08 else "flat",
        "volatility": vol_key,
        "ma_short": round(ma_short, 6),
        "ma_long": round(ma_long, 6),
        "momentum_pct_10m": round(mom_pct, 4),
        "candle_count": n,
        "source": source_hint,
        "what_the_bot_saw": saw_lines,
    }


def plain_allow_block_hint(context: dict | None, verdict: str | None) -> str:
    if not context:
        return "Not enough candle history yet — the bot leans on fresh snapshots until more bars load."
    tr = context.get("trend", "sideways")
    vol = context.get("volatility", "normal")
    if verdict == "skip":
        return "The bot stood aside this cycle (no entry) — that is different from a hard safety block."
    if verdict == "block":
        if vol == "elevated":
            return "With jumpier bars on the chart, the safety layer is more likely to say wait — even if the trend looks tempting."
        return "Even when the chart shows a direction, the safety layer can still stop a trade if rules or snapshot flags disagree."
    if verdict == "allow_with_reduction":
        return "The chart context looked tradeable, but size was trimmed to stay inside risk limits — like only spending part of an allowance."
    if verdict == "allow":
        return "The recent candle picture and the safety checks both lined up enough to allow a small paper trade."
    return "When a trade is blocked, it is usually a mismatch between price action, confidence, and the safety rules — not because the chart is 'wrong'."
