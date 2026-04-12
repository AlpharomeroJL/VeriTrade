from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SystemControl(Base):
    __tablename__ = "system_control"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(String(32), default="stopped")  # running, paused, stopped
    manual_pause: Mapped[bool] = mapped_column(Boolean, default=False)
    no_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    price: Mapped[float] = mapped_column(Float)
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(64), default="mock")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MarketCandle(Base):
    """Closed (or best-effort) OHLC bars for charting and strategy warm-up — paper execution unchanged."""

    __tablename__ = "market_candles"
    __table_args__ = (UniqueConstraint("symbol", "interval_minutes", "open_time", name="uq_market_candle_bucket"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=1, index=True)
    open_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(64), default="kraken_ohlc")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    signal_type: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text, default="")
    strategy_id: Mapped[str] = mapped_column(String(64), default="baseline_ma")
    market_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("market_snapshots.id"), nullable=True)

    market_snapshot: Mapped["MarketSnapshot | None"] = relationship()


class RiskDecision(Base):
    __tablename__ = "risk_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    related_signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    verdict: Mapped[str] = mapped_column(String(32))
    reasons: Mapped[str] = mapped_column(Text, default="[]")
    policy_version: Mapped[str] = mapped_column(String(32))
    approved_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    requested_size: Mapped[float | None] = mapped_column(Float, nullable=True)


class TradeIntent(Base):
    __tablename__ = "trade_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intent_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    asset: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(16))
    requested_size: Mapped[float] = mapped_column(Float)
    approved_size: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float)
    strategy_id: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(32))
    risk_verdict: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="proposed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    risk_decision_id: Mapped[int | None] = mapped_column(ForeignKey("risk_decisions.id"), nullable=True)
    lane_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    lane_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    strategy_family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capital_bucket: Mapped[float | None] = mapped_column(Float, nullable=True)


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intent_id: Mapped[int] = mapped_column(ForeignKey("trade_intents.id"), index=True)
    venue: Mapped[str] = mapped_column(String(32), default="paper")
    order_type: Mapped[str] = mapped_column(String(32), default="market")
    status: Mapped[str] = mapped_column(String(32), index=True)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    lane_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    market_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    strategy_family: Mapped[str | None] = mapped_column(String(64), nullable=True)

    intent: Mapped["TradeIntent"] = relationship()


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    related_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(32), default="recorded")
    payload_summary: Mapped[str] = mapped_column(Text, default="{}")


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    equity: Mapped[float] = mapped_column(Float)
    pnl_daily: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_total: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    position_notional: Mapped[float] = mapped_column(Float, default=0.0)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    severity: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")


class KrakenSkillSession(Base):
    __tablename__ = "kraken_skill_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_type: Mapped[str] = mapped_column(String(32), index=True)
    operation: Mapped[str] = mapped_column(String(64), index=True)
    symbols_json: Mapped[str] = mapped_column(Text, default="[]")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    logs_json: Mapped[str] = mapped_column(Text, default="[]")
    outputs_json: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    rationale: Mapped[str] = mapped_column(Text, default="")


class TradingLaneState(Base):
    __tablename__ = "trading_lane_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lane_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    lane_label: Mapped[str] = mapped_column(String(64))
    market_type: Mapped[str] = mapped_column(String(16))
    strategy_family: Mapped[str] = mapped_column(String(64))
    default_symbols_json: Mapped[str] = mapped_column(Text, default="[]")
    capital_allocation: Mapped[float] = mapped_column(Float, default=5000.0)
    risk_profile: Mapped[str] = mapped_column(String(64), default="balanced")
    cadence_seconds: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(24), default="stopped", index=True)
    last_outcome: Mapped[str] = mapped_column(String(32), default="idle")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LanePerformanceSnapshot(Base):
    __tablename__ = "lane_performance_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lane_id: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    equity: Mapped[float] = mapped_column(Float)
    pnl_daily: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_total: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    open_notional: Mapped[float] = mapped_column(Float, default=0.0)
    turnover: Mapped[float] = mapped_column(Float, default=0.0)
    allow_count: Mapped[int] = mapped_column(Integer, default=0)
    reduce_count: Mapped[int] = mapped_column(Integer, default=0)
    block_count: Mapped[int] = mapped_column(Integer, default=0)
    skip_count: Mapped[int] = mapped_column(Integer, default=0)
