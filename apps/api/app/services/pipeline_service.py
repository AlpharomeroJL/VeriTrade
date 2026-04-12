from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Alert
from app.services import (
    artifact_service,
    candle_service,
    control_service,
    execution_service,
    intent_service,
    market_service,
    performance_service,
    risk_engine,
    strategy_service,
)


def run_strategy_cycle(
    db: Session,
    *,
    ingest_market: bool = True,
    force_step: bool = False,
    deterministic_signal: tuple[str, float] | None = None,
) -> dict:
    settings = get_settings()
    ctrl = control_service.get_or_create_control(db)
    if ctrl.mode == "stopped":
        return {"ok": False, "error": "system_stopped"}
    if ctrl.mode == "paused" and not force_step:
        return {"ok": False, "error": "system_paused"}

    if ingest_market:
        snapshot = market_service.ingest_for_settings(db)
    else:
        snapshot = market_service.get_latest_snapshot(db)
        if snapshot is None:
            snapshot = market_service.ingest_for_settings(db)

    if market_service.snapshot_is_stale(snapshot):
        pass

    candle_service.refresh_candles_for_symbol(db, snapshot.symbol, target_bars=480)

    if deterministic_signal is not None:
        stype, conf = deterministic_signal
        signal = strategy_service.create_deterministic_signal(
            db, snapshot, signal_type=stype, confidence=conf
        )
    else:
        signal = strategy_service.generate_signal_from_snapshot(db, snapshot)

    artifact_service.write_artifact(
        db,
        "signal",
        str(signal.id),
        {
            "signal_id": signal.id,
            "asset": signal.asset,
            "type": signal.signal_type,
            "confidence": signal.confidence,
            "rationale": signal.rationale,
        },
    )

    requested_notional = min(
        settings.default_max_position_notional,
        settings.default_max_position_notional * signal.confidence,
    )

    risk_result = risk_engine.evaluate_signal(
        db,
        signal,
        requested_notional,
        snapshot.captured_at,
        snapshot.volatility_flag,
        ctrl.manual_pause,
        ctrl.no_trade,
    )
    risk_row = risk_engine.persist_risk_decision(db, signal, risk_result, settings.policy_version)

    artifact_service.write_artifact(
        db,
        "risk",
        str(risk_row.id),
        {
            "risk_decision_id": risk_row.id,
            "signal_id": signal.id,
            "verdict": risk_result.verdict,
            "reasons": risk_result.reasons,
            "approved_notional": risk_result.approved_size,
        },
    )

    if risk_result.verdict == "block":
        al = Alert(
            severity="warn",
            category="risk_block",
            message=f"Blocked signal {signal.id}: {risk_result.reasons}",
            created_at=datetime.utcnow(),
            status="open",
        )
        db.add(al)
        db.commit()
        return {
            "ok": True,
            "blocked": True,
            "signal_id": signal.id,
            "risk_decision_id": risk_row.id,
            "verdict": risk_result.verdict,
            "lane_id": None,
            "lane_label": "Core demo pipeline",
        }

    if risk_result.verdict == "skip":
        return {
            "ok": True,
            "blocked": False,
            "skipped": True,
            "signal_id": signal.id,
            "risk_decision_id": risk_row.id,
            "verdict": risk_result.verdict,
            "lane_id": None,
            "lane_label": "Core demo pipeline",
        }

    if risk_result.verdict == "escalate_for_review":
        intent = intent_service.create_intent(
            db,
            asset=signal.asset,
            action=signal.signal_type if signal.signal_type != "hold" else "hold",
            requested_size=requested_notional,
            approved_size=0.0,
            rationale=signal.rationale,
            confidence=signal.confidence,
            strategy_id=signal.strategy_id,
            policy_version=settings.policy_version,
            risk_verdict=risk_result.verdict,
            signal_id=signal.id,
            risk_decision_id=risk_row.id,
            status="escalated_for_review",
        )
        artifact_service.write_artifact(
            db,
            "intent",
            str(intent.id),
            {"intent_id": intent.id, "uuid": intent.intent_uuid, "status": intent.status},
        )
        return {
            "ok": True,
            "escalated": True,
            "signal_id": signal.id,
            "risk_decision_id": risk_row.id,
            "intent_id": intent.id,
        }

    intent = intent_service.create_intent(
        db,
        asset=signal.asset,
        action=signal.signal_type,
        requested_size=risk_result.requested_size,
        approved_size=risk_result.approved_size,
        rationale=signal.rationale,
        confidence=signal.confidence,
        strategy_id=signal.strategy_id,
        policy_version=settings.policy_version,
        risk_verdict=risk_result.verdict,
        signal_id=signal.id,
        risk_decision_id=risk_row.id,
        status="approved",
    )
    artifact_service.write_artifact(
        db,
        "intent",
        str(intent.id),
        {
            "intent_id": intent.id,
            "uuid": intent.intent_uuid,
            "action": intent.action,
            "approved_notional": intent.approved_size,
        },
    )

    ex = execution_service.simulate_execution(db, intent, snapshot.price)
    artifact_service.write_artifact(
        db,
        "execution",
        str(ex.id),
        {
            "execution_id": ex.id,
            "intent_id": intent.id,
            "status": ex.status,
            "fill_price": ex.fill_price,
            "fill_size": ex.fill_size,
        },
    )

    if ex.status == "filled":
        performance_service.apply_execution_to_performance(db, ex)

    return {
        "ok": True,
        "blocked": False,
        "signal_id": signal.id,
        "risk_decision_id": risk_row.id,
        "intent_id": intent.id,
        "execution_id": ex.id,
        "execution_status": ex.status,
        "verdict": risk_result.verdict,
        "lane_id": None,
        "lane_label": "Core demo pipeline",
    }


DEMO_SCENARIOS = frozenset({"safe_allow", "volatile_block", "oversized_reduce"})


def _wipe_demo_tables(db: Session) -> None:
    from sqlalchemy import delete

    from app.models import (
        Artifact,
        Execution,
        KrakenSkillSession,
        LanePerformanceSnapshot,
        MarketCandle,
        MarketSnapshot,
        PerformanceSnapshot,
        RiskDecision,
        Signal,
        TradeIntent,
        TradingLaneState,
    )

    for model in (
        Artifact,
        Execution,
        TradeIntent,
        RiskDecision,
        Signal,
        MarketSnapshot,
        MarketCandle,
        PerformanceSnapshot,
        KrakenSkillSession,
        LanePerformanceSnapshot,
        TradingLaneState,
        Alert,
    ):
        db.execute(delete(model))
    db.commit()


def demo_seed(db: Session) -> dict:
    _wipe_demo_tables(db)
    ctrl = control_service.get_or_create_control(db)
    ctrl.mode = "running"
    ctrl.manual_pause = False
    ctrl.no_trade = False
    db.add(ctrl)
    db.commit()

    performance_service.seed_starting_performance(db)
    snap = market_service.ingest_for_settings(db)
    # Minute-spaced demo tape so 1m candle aggregation + chart are usable before extra cycles.
    floor = datetime.utcnow().replace(second=0, microsecond=0)
    sym = snap.symbol
    for i in range(1, 4):
        market_service.ingest_mock_snapshot(
            db,
            symbol=sym,
            volatility_flag=False,
            captured_at=floor - timedelta(minutes=i),
        )
    return {"ok": True, "market_snapshot_id": snap.id}


def demo_run_scenario(db: Session, scenario: str) -> dict:
    """Deterministic judge-visible outcomes: allow / block / trim — no random signal or vol."""
    assert scenario in DEMO_SCENARIOS
    _wipe_demo_tables(db)
    ctrl = control_service.get_or_create_control(db)
    ctrl.mode = "running"
    ctrl.manual_pause = False
    ctrl.no_trade = False
    db.add(ctrl)
    db.commit()

    performance_service.seed_starting_performance(db)
    if scenario == "oversized_reduce":
        performance_service.set_open_position_notional(db, 430.0)

    vol = scenario == "volatile_block"
    snap = market_service.ingest_mock_snapshot(db, volatility_flag=vol)

    result = run_strategy_cycle(
        db,
        ingest_market=False,
        force_step=False,
        deterministic_signal=("buy", 0.92),
    )
    result["scenario"] = scenario
    result["market_snapshot_id"] = snap.id
    return result
