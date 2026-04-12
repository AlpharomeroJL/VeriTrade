from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Alert,
    Artifact,
    Execution,
    MarketSnapshot,
    PerformanceSnapshot,
    RiskDecision,
    Signal,
    TradeIntent,
)
from app.adapters.kraken_public_market import TOP_UI_SYMBOLS
from app.challenge.context import build_challenge_context
from app.challenge.intent_commitment import intent_commitment_sha256
from app.schemas.api import (
    ActivityItem,
    AlertOut,
    ArtifactOut,
    CandlestickOut,
    ChallengeContextOut,
    ControlStateOut,
    ExecutionOut,
    IntentOut,
    KrakenSkillRunRequest,
    KrakenSkillSessionOut,
    LaneHistoryItemOut,
    LanePerformanceOut,
    MarketChartPackOut,
    MarketChartPointOut,
    MarketContextOut,
    OverviewOut,
    PaperSessionOut,
    PerformanceOut,
    RiskDecisionOut,
    SignalOut,
    TopMarketRowOut,
    TradeMarkerOut,
    TradingLaneOut,
)
from app.services import autonomous_service, control_service, kraken_skills_service, lane_service, pipeline_service, rubric_service, viz_service

_CHART_INTERVALS: dict[str, int] = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60}

router = APIRouter()


def _intent_out_with_commitment(row: TradeIntent | None) -> IntentOut | None:
    if row is None:
        return None
    base = IntentOut.model_validate(row)
    return base.model_copy(update={"intent_commitment_sha256": intent_commitment_sha256(row)})


def _control_out(db: Session) -> ControlStateOut:
    s = get_settings()
    c = control_service.get_or_create_control(db)
    return ControlStateOut(
        mode=c.mode,
        manual_pause=c.manual_pause,
        no_trade=c.no_trade,
        trading_mode=s.trading_mode,
        execution_provider=s.execution_provider,
    )


@router.get("/health")
def health():
    return {"status": "ok", "service": "veritrade-api"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        control_service.get_or_create_control(db)
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


def _latest_market_for_symbol(db: Session, symbol: str) -> MarketSnapshot | None:
    q = (
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol)
        .order_by(desc(MarketSnapshot.captured_at))
        .limit(1)
    )
    return db.execute(q).scalar_one_or_none()


@router.get("/overview", response_model=OverviewOut)
def overview(db: Session = Depends(get_db)):
    """Latest signal / intent / execution are anchored to the newest risk decision so UI panels describe one cycle."""
    latest_risk = db.execute(select(RiskDecision).order_by(desc(RiskDecision.timestamp)).limit(1)).scalar_one_or_none()
    latest_sig = None
    latest_intent = None
    latest_ex = None
    if latest_risk is not None:
        latest_sig = db.get(Signal, latest_risk.related_signal_id)
        latest_intent = db.execute(
            select(TradeIntent)
            .where(TradeIntent.risk_decision_id == latest_risk.id)
            .order_by(desc(TradeIntent.created_at))
            .limit(1)
        ).scalar_one_or_none()
        if latest_intent is not None:
            latest_ex = db.execute(
                select(Execution)
                .where(Execution.intent_id == latest_intent.id)
                .order_by(desc(Execution.created_at))
                .limit(1)
            ).scalar_one_or_none()
    else:
        latest_sig = db.execute(select(Signal).order_by(desc(Signal.timestamp)).limit(1)).scalar_one_or_none()
        latest_intent = db.execute(select(TradeIntent).order_by(desc(TradeIntent.created_at)).limit(1)).scalar_one_or_none()
        latest_ex = db.execute(select(Execution).order_by(desc(Execution.created_at)).limit(1)).scalar_one_or_none()
    latest_perf = db.execute(select(PerformanceSnapshot).order_by(desc(PerformanceSnapshot.timestamp)).limit(1)).scalar_one_or_none()
    s = get_settings()
    sym = (s.default_symbol or "BTCUSD").upper()
    snap = _latest_market_for_symbol(db, sym)
    market = None
    if snap:
        market = {
            "symbol": snap.symbol,
            "price": snap.price,
            "bid": snap.bid,
            "ask": snap.ask,
            "source": snap.source,
            "captured_at": snap.captured_at.isoformat(),
            "volatility_flag": snap.volatility_flag,
        }
    challenge = build_challenge_context(latest_intent, snap)
    rubric, fit = rubric_service.rubric_and_fit(db)
    strip = rubric_service.build_safety_strip(s, fit)
    lane_trust = rubric_service.compute_lane_trust_summaries(db)

    top_markets: list[TopMarketRowOut] = []
    for t_sym in TOP_UI_SYMBOLS:
        row = _latest_market_for_symbol(db, t_sym)
        if row:
            top_markets.append(
                TopMarketRowOut(
                    symbol=row.symbol,
                    price=row.price,
                    bid=row.bid,
                    ask=row.ask,
                    source=row.source,
                    captured_at=row.captured_at,
                )
            )

    return OverviewOut(
        control=_control_out(db),
        challenge=challenge,
        rubric_metrics=rubric,
        challenge_fit=fit,
        safety_strip=strip,
        autonomous=autonomous_service.get_status(),
        cycle_history=autonomous_service.get_recent_history(limit=20),
        lane_trust=lane_trust,
        top_markets=top_markets,
        latest_signal=SignalOut.model_validate(latest_sig) if latest_sig else None,
        latest_risk=RiskDecisionOut.model_validate(latest_risk) if latest_risk else None,
        latest_intent=_intent_out_with_commitment(latest_intent),
        latest_execution=ExecutionOut.model_validate(latest_ex) if latest_ex else None,
        latest_performance=PerformanceOut.model_validate(latest_perf) if latest_perf else None,
        market_snapshot=market,
    )


@router.get("/challenge/context", response_model=ChallengeContextOut)
def challenge_context(db: Session = Depends(get_db)):
    latest_intent = db.execute(select(TradeIntent).order_by(desc(TradeIntent.created_at)).limit(1)).scalar_one_or_none()
    snap = db.execute(select(MarketSnapshot).order_by(desc(MarketSnapshot.captured_at)).limit(1)).scalar_one_or_none()
    return build_challenge_context(latest_intent, snap)


@router.get("/performance", response_model=list[PerformanceOut])
def performance_list(db: Session = Depends(get_db), limit: int = 50):
    q = select(PerformanceSnapshot).order_by(desc(PerformanceSnapshot.timestamp)).limit(min(limit, 200))
    rows = db.execute(q).scalars().all()
    return [PerformanceOut.model_validate(r) for r in rows]


@router.get("/viz/market-chart", response_model=MarketChartPackOut)
def viz_market_chart(
    db: Session = Depends(get_db),
    symbol: str | None = None,
    limit: int = 360,
    interval: str = Query("1m", description="Candle width: 1m, 5m, 15m, 30m, 1h"),
):
    s = get_settings()
    sym = (symbol or s.default_symbol or "BTCUSD").upper()
    key = (interval or "1m").strip().lower()
    if key not in _CHART_INTERVALS:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_interval", "allowed": sorted(_CHART_INTERVALS)},
        )
    iv = _CHART_INTERVALS[key]
    pack = viz_service.market_chart_pack_data(db, sym, limit, interval_minutes=iv, interval_code=key)
    ctx = pack.get("context")
    return MarketChartPackOut(
        symbol=pack["symbol"],
        interval=pack.get("interval", key),
        candles=[
            CandlestickOut(
                t=c["t"],
                o=c["o"],
                h=c["h"],
                l=c["l"],
                c=c["c"],
                v=float(c.get("v", 0.0)),
                forming=bool(c.get("forming", False)),
            )
            for c in pack["candles"]
        ],
        points=[MarketChartPointOut(t=p["t"], price=p["price"]) for p in pack["points"]],
        markers=[TradeMarkerOut(ts=m["ts"], price=m["price"], kind=m["kind"], label=m["label"]) for m in pack["markers"]],
        context=MarketContextOut.model_validate(ctx) if ctx else None,
    )


@router.get("/viz/paper-session", response_model=PaperSessionOut)
def viz_paper_session(db: Session = Depends(get_db)):
    agg = viz_service.paper_session_summary(db)
    latest_perf = db.execute(select(PerformanceSnapshot).order_by(desc(PerformanceSnapshot.timestamp)).limit(1)).scalar_one_or_none()
    equity = float(latest_perf.equity) if latest_perf else None
    pnl_total = float(latest_perf.pnl_total) if latest_perf else None
    pnl_daily = float(latest_perf.pnl_daily) if latest_perf else None
    pos = float(latest_perf.position_notional) if latest_perf else None
    return PaperSessionOut(
        **agg,
        equity=equity,
        pnl_total=pnl_total,
        pnl_daily=pnl_daily,
        position_notional=pos,
    )


@router.get("/activity", response_model=list[ActivityItem])
def activity(db: Session = Depends(get_db), limit: int = 100):
    q = select(Artifact).order_by(desc(Artifact.timestamp)).limit(min(limit, 500))
    rows = db.execute(q).scalars().all()
    out: list[ActivityItem] = []
    for a in rows:
        summary = a.payload_summary[:500] if a.payload_summary else ""
        out.append(
            ActivityItem(
                id=a.id,
                kind=a.artifact_type,
                timestamp=a.timestamp,
                summary=summary,
                verdict_or_status=a.status,
                related_id=a.related_id,
            )
        )
    return out


@router.get("/signals", response_model=list[SignalOut])
def signals(db: Session = Depends(get_db), limit: int = 50):
    q = select(Signal).order_by(desc(Signal.timestamp)).limit(min(limit, 200))
    return [SignalOut.model_validate(r) for r in db.execute(q).scalars().all()]


@router.get("/risk-decisions", response_model=list[RiskDecisionOut])
def risk_decisions(db: Session = Depends(get_db), limit: int = 50):
    q = select(RiskDecision).order_by(desc(RiskDecision.timestamp)).limit(min(limit, 200))
    return [RiskDecisionOut.model_validate(r) for r in db.execute(q).scalars().all()]


@router.get("/intents", response_model=list[IntentOut])
def intents(db: Session = Depends(get_db), limit: int = 50):
    q = select(TradeIntent).order_by(desc(TradeIntent.created_at)).limit(min(limit, 200))
    return [IntentOut.model_validate(r) for r in db.execute(q).scalars().all()]


@router.get("/executions", response_model=list[ExecutionOut])
def executions(db: Session = Depends(get_db), limit: int = 50):
    q = select(Execution).order_by(desc(Execution.created_at)).limit(min(limit, 200))
    return [ExecutionOut.model_validate(r) for r in db.execute(q).scalars().all()]


@router.get("/artifacts", response_model=list[ArtifactOut])
def artifacts(db: Session = Depends(get_db), limit: int = 100):
    q = select(Artifact).order_by(desc(Artifact.timestamp)).limit(min(limit, 500))
    return [ArtifactOut.model_validate(r) for r in db.execute(q).scalars().all()]


@router.get("/alerts", response_model=list[AlertOut])
def alerts(db: Session = Depends(get_db), limit: int = 50):
    q = select(Alert).order_by(desc(Alert.created_at)).limit(min(limit, 200))
    return [AlertOut.model_validate(r) for r in db.execute(q).scalars().all()]


@router.post("/control/start")
def control_start(db: Session = Depends(get_db)):
    control_service.set_mode(db, "running")
    return {"ok": True, "mode": "running"}


@router.post("/control/pause")
def control_pause(db: Session = Depends(get_db)):
    control_service.set_mode(db, "paused")
    return {"ok": True, "mode": "paused"}


@router.post("/control/stop")
def control_stop(db: Session = Depends(get_db)):
    control_service.set_mode(db, "stopped")
    return {"ok": True, "mode": "stopped"}


@router.post("/control/manual-pause")
def control_manual_pause(enabled: bool, db: Session = Depends(get_db)):
    control_service.set_manual_pause(db, enabled)
    return {"ok": True, "manual_pause": enabled}


@router.post("/control/step")
def control_step(db: Session = Depends(get_db)):
    return pipeline_service.run_strategy_cycle(db, force_step=True)


@router.post("/control/autonomous/start")
def control_autonomous_start(cadence_seconds: int = 15):
    return {"ok": True, "autonomous": autonomous_service.start_autonomous(cadence_seconds)}


@router.post("/control/autonomous/stop")
def control_autonomous_stop():
    return {"ok": True, "autonomous": autonomous_service.stop_autonomous()}


@router.post("/demo/seed")
def demo_seed(db: Session = Depends(get_db)):
    return pipeline_service.demo_seed(db)


@router.post("/demo/run-once")
def demo_run_once(db: Session = Depends(get_db)):
    return pipeline_service.run_strategy_cycle(db, force_step=False)


@router.post("/demo/scenario/{scenario_id}")
def demo_scenario(scenario_id: str, db: Session = Depends(get_db)):
    if scenario_id not in pipeline_service.DEMO_SCENARIOS:
        raise HTTPException(status_code=400, detail="unknown_scenario")
    return pipeline_service.demo_run_scenario(db, scenario_id)


@router.post("/kraken-skills/run", response_model=KrakenSkillSessionOut)
def kraken_skills_run(payload: KrakenSkillRunRequest, db: Session = Depends(get_db)):
    row = kraken_skills_service.run_operation(
        db,
        operation=payload.operation,
        symbols=payload.symbols,
        lane_id=payload.lane_id,
        starting_capital=payload.starting_capital,
        strategy=payload.strategy,
        alert_price=payload.alert_price,
        drop_percent=payload.drop_percent,
    )
    return KrakenSkillSessionOut.model_validate(row)


@router.get("/kraken-skills/sessions", response_model=list[KrakenSkillSessionOut])
def kraken_skills_sessions(db: Session = Depends(get_db), limit: int = 30):
    return [KrakenSkillSessionOut.model_validate(r) for r in kraken_skills_service.list_sessions(db, limit=limit)]


@router.get("/kraken-skills/sessions/{session_id}", response_model=KrakenSkillSessionOut)
def kraken_skills_session(session_id: int, db: Session = Depends(get_db)):
    row = kraken_skills_service.get_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return KrakenSkillSessionOut.model_validate(row)


@router.get("/lanes", response_model=list[TradingLaneOut])
def lanes(db: Session = Depends(get_db)):
    return [TradingLaneOut.model_validate(r) for r in lane_service.list_lanes(db)]


@router.get("/lanes/{lane_id}", response_model=TradingLaneOut)
def lane(lane_id: str, db: Session = Depends(get_db)):
    row = lane_service.get_lane(db, lane_id)
    if row is None:
        raise HTTPException(status_code=404, detail="lane_not_found")
    return TradingLaneOut.model_validate(row)


@router.get("/lanes/{lane_id}/performance", response_model=list[LanePerformanceOut])
def lane_performance(lane_id: str, db: Session = Depends(get_db), limit: int = 60):
    return [LanePerformanceOut.model_validate(r) for r in lane_service.get_lane_performance(db, lane_id, limit=limit)]


@router.get("/lanes/{lane_id}/history", response_model=list[LaneHistoryItemOut])
def lane_history(lane_id: str, db: Session = Depends(get_db), limit: int = 40):
    return [LaneHistoryItemOut.model_validate(r) for r in lane_service.get_lane_history(db, lane_id, limit=limit)]


@router.post("/lanes/{lane_id}/start", response_model=TradingLaneOut)
def lane_start(lane_id: str, db: Session = Depends(get_db)):
    row = lane_service.set_lane_status(db, lane_id, "running")
    if row is None:
        raise HTTPException(status_code=404, detail="lane_not_found")
    return TradingLaneOut.model_validate(row)


@router.post("/lanes/{lane_id}/stop", response_model=TradingLaneOut)
def lane_stop(lane_id: str, db: Session = Depends(get_db)):
    row = lane_service.set_lane_status(db, lane_id, "stopped")
    if row is None:
        raise HTTPException(status_code=404, detail="lane_not_found")
    return TradingLaneOut.model_validate(row)


@router.post("/lanes/{lane_id}/run-once")
def lane_run_once(lane_id: str, db: Session = Depends(get_db)):
    out = lane_service.run_lane_once(db, lane_id)
    if out.get("error") == "lane_not_found":
        raise HTTPException(status_code=404, detail="lane_not_found")
    return out
