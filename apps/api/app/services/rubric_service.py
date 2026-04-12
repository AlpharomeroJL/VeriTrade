"""Narrow demo metrics for challenge rubric panels — simple, explainable counts."""

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.adapters.kraken_execution_surface import KrakenSurfaceStatus, get_surface_status
from app.config import Settings, get_settings
from app.models import Artifact, Execution, LanePerformanceSnapshot, RiskDecision, TradeIntent
from app.schemas.api import ChallengeFitOut, LaneTrustSummaryOut, RubricMetricsOut, SafetyStripOut
from app.services.lane_service import LANE_DEFS


def _artifact_count_for_lane_intents(db: Session, rows: list[TradeIntent]) -> int:
    """Count artifacts whose related_id matches signal/risk/intent/execution IDs for these intents."""
    if not rows:
        return 0
    related: set[str] = set()
    intent_ids: list[int] = []
    for r in rows:
        intent_ids.append(r.id)
        related.add(str(r.id))
        if r.signal_id is not None:
            related.add(str(r.signal_id))
        if r.risk_decision_id is not None:
            related.add(str(r.risk_decision_id))
    exec_ids = db.execute(select(Execution.id).where(Execution.intent_id.in_(intent_ids))).scalars().all()
    for eid in exec_ids:
        related.add(str(eid))
    return int(db.scalar(select(func.count()).select_from(Artifact).where(Artifact.related_id.in_(related)))) or 0


def compute_lane_trust_summaries(db: Session) -> list[LaneTrustSummaryOut]:
    """Aggregate risk outcomes per trading lane from persisted intents (lane-scoped runs)."""
    out: list[LaneTrustSummaryOut] = []
    for lane_id, cfg in LANE_DEFS.items():
        rows = db.execute(select(TradeIntent).where(TradeIntent.lane_id == lane_id)).scalars().all()
        allow_c = sum(1 for r in rows if r.risk_verdict == "allow")
        reduce_c = sum(1 for r in rows if r.risk_verdict == "allow_with_reduction")
        block_c = sum(1 for r in rows if r.risk_verdict == "block")
        review_c = sum(1 for r in rows if r.risk_verdict == "escalate_for_review")
        passed = allow_c + reduce_c
        raw = 42 + min(28, passed * 4) + min(12, reduce_c * 2) - min(28, block_c * 9) - min(12, review_c * 3)
        score = max(0, min(100, raw))
        label = cfg["lane_label"]
        mt = cfg["market_type"]
        if block_c > passed and len(rows) >= 2:
            posture = (
                f"{label}: cautious right now — more blocks than passes"
                if mt == "futures_paper"
                else f"{label}: cautious — spot lane is prioritizing safety over frequency"
            )
        elif score >= 74:
            posture = (
                f"{label}: tactical flow looks disciplined (paper)"
                if mt == "futures_paper"
                else f"{label}: spot lane is behaving — steady governed passes"
            )
        elif score >= 52:
            posture = f"{label}: mixed — evidence still building"
        else:
            posture = f"{label}: early session — few lane decisions yet"
        art_n = _artifact_count_for_lane_intents(db, rows)
        lane_skip = int(
            db.scalar(
                select(LanePerformanceSnapshot.skip_count)
                .where(LanePerformanceSnapshot.lane_id == lane_id)
                .order_by(desc(LanePerformanceSnapshot.timestamp))
                .limit(1)
            )
            or 0
        )
        expl = (
            f"Plain view: {art_n} validation artifacts tie back to this lane’s last decisions (signal → risk → intent → execution). "
            f"Counts from intents — allowed {allow_c}, reduced {reduce_c}, blocked {block_c}, review {review_c}. "
            f"Stand-asides (no trade, not hard blocks) from lane ledger: {lane_skip}. "
            "More clean passes with artifacts strengthen lane trust."
        )
        out.append(
            LaneTrustSummaryOut(
                lane_id=lane_id,
                lane_label=label,
                market_type=cfg["market_type"],
                allow_count=allow_c,
                reduce_count=reduce_c,
                block_count=block_c,
                review_count=review_c,
                stand_aside_count=lane_skip,
                artifact_count=art_n,
                trust_score_0_100=score,
                posture_label=posture,
                explainer_one_liner=expl,
            )
        )
    return out


def compute_rubric_metrics(db: Session) -> RubricMetricsOut:
    ac = int(db.scalar(select(func.count()).select_from(Artifact)) or 0)
    allow_full = int(
        db.scalar(select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "allow")) or 0
    )
    reduced = int(
        db.scalar(
            select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "allow_with_reduction")
        )
        or 0
    )
    allow_trim = allow_full + reduced
    block_n = int(
        db.scalar(select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "block")) or 0
    )
    skip_n = int(
        db.scalar(select(func.count()).select_from(RiskDecision).where(RiskDecision.verdict == "skip")) or 0
    )
    raw = 40 + min(28, ac * 2) + min(14, allow_full * 4) + min(12, reduced * 4) - min(30, block_n * 10)
    score = max(0, min(100, raw))
    if block_n > allow_trim and ac >= 3:
        posture = "Safety-heavy — more blocks than passes in this session"
    elif score >= 78:
        posture = "Strong audit posture"
    elif score >= 55:
        posture = "Balanced — evidence accumulating"
    else:
        posture = "Early or constrained — run more governed cycles"
    explainer = (
        f"Weights artifact records ({ac}), full allows ({allow_full}), size reductions ({reduced}), hard blocks ({block_n}), "
        f"and stand-asides ({skip_n}) — skips are passive no-trade, not safety failures. "
        "More evidence and successful passes raise the score; hard blocks pull it down."
    )
    return RubricMetricsOut(
        validation_artifact_count=ac,
        risk_full_allow_count=allow_full,
        risk_reduced_count=reduced,
        risk_allow_or_trim_count=allow_trim,
        risk_block_count=block_n,
        risk_skip_count=skip_n,
        trust_score_0_100=score,
        trust_posture_label=posture,
        trust_score_explainer=explainer,
    )


def compute_challenge_fit(
    db: Session,
    settings: Settings,
    rubric: RubricMetricsOut,
    surface: KrakenSurfaceStatus,
) -> ChallengeFitOut:
    risk_n = int(db.scalar(select(func.count()).select_from(RiskDecision)) or 0)
    stub = (settings.erc8004_agent_uri_stub or "").strip()
    kraken_aligned = bool(settings.kraken_cli_surface_enabled) or bool(
        (surface.cli_command_stub or "").strip()
    )
    return ChallengeFitOut(
        kraken_execution_surface_aligned=kraken_aligned,
        erc8004_identity_hooks=bool(stub),
        combined_submission_story=True,
        paper_safe_demo_mode=settings.trading_mode == "paper" and not settings.allow_real_orders,
        risk_router_active=risk_n > 0,
        validation_artifacts_active=rubric.validation_artifact_count > 0,
    )


def rubric_and_fit(db: Session) -> tuple[RubricMetricsOut, ChallengeFitOut]:
    s = get_settings()
    rubric = compute_rubric_metrics(db)
    fit = compute_challenge_fit(db, s, rubric, get_surface_status())
    return rubric, fit


def build_safety_strip(settings: Settings, fit: ChallengeFitOut) -> SafetyStripOut:
    mode = (settings.market_data_mode or "demo").lower()
    if mode == "kraken_public":
        label = "Kraken public ticker"
        detail = (
            "Live BTC/USD, ETH/USD, SOL/USD from Kraken /public/Ticker over HTTPS. "
            "No API keys; read-only. Execution stays on the paper adapter unless live gates are armed."
        )
    elif mode == "kraken_cli":
        label = "Kraken CLI ticker"
        detail = (
            "Reads BTC/USD, ETH/USD, SOL/USD from an external Kraken CLI command template "
            "(KRAKEN_MARKET_CLI_TICKER_TEMPLATE). If CLI is missing or fails, UI labels fallback explicitly."
        )
    else:
        label = "Demo snapshots"
        detail = (
            "Synthetic prices for repeatable demos and scenario presets. Set MARKET_DATA_MODE=kraken_public "
            "or MARKET_DATA_MODE=kraken_cli to ingest live Kraken top-of-book for the same three pairs."
        )
    live_on = bool(settings.allow_real_orders and settings.enable_kraken_execution)
    return SafetyStripOut(
        market_data_mode=mode,
        market_mode_label=label,
        market_data_detail=detail,
        execution_mode=f"{settings.trading_mode} · {settings.execution_provider}",
        paper_safe_execution=bool(settings.trading_mode == "paper" and not live_on),
        live_trading_enabled=live_on,
        risk_router_active=fit.risk_router_active,
        validation_artifacts_active=fit.validation_artifacts_active,
    )
