from datetime import datetime

from pydantic import BaseModel, Field


class SignalOut(BaseModel):
    id: int
    asset: str
    timestamp: datetime
    signal_type: str
    confidence: float
    rationale: str
    strategy_id: str
    market_snapshot_id: int | None = None

    model_config = {"from_attributes": True}


class RiskDecisionOut(BaseModel):
    id: int
    related_signal_id: int
    timestamp: datetime
    verdict: str
    reasons: str
    policy_version: str
    approved_size: float | None = None
    requested_size: float | None = None

    model_config = {"from_attributes": True}


class IntentOut(BaseModel):
    id: int
    intent_uuid: str
    asset: str
    action: str
    requested_size: float
    approved_size: float
    rationale: str
    confidence: float
    strategy_id: str
    policy_version: str
    risk_verdict: str
    status: str
    created_at: datetime
    signal_id: int | None = None
    risk_decision_id: int | None = None
    intent_commitment_sha256: str | None = None
    lane_id: str | None = None
    lane_label: str | None = None
    market_type: str | None = None
    strategy_family: str | None = None
    capital_bucket: float | None = None
    eip712_signature: str | None = None
    eip712_signer: str | None = None
    eip712_chain_id: int | None = None

    model_config = {"from_attributes": True}


class IntentSignatureVerificationOut(BaseModel):
    """EIP-712 digest + optional EOA recover + optional ERC-1271 eth_call (adapter verifyingContract)."""

    intent_id: int
    intent_commitment_sha256: str
    eip712_digest_hex: str
    eip712_typed_data: dict | None = None
    eip712_typed_data_included: bool = False
    eip712_recovered_address: str | None = None
    eip712_signature_valid_for_digest: bool | None = None
    eip1271_eth_call: dict | None = None
    eip1271_secondary_eth_call: dict | None = None
    notes: list[str] = Field(default_factory=list)


class ExecutionOut(BaseModel):
    id: int
    intent_id: int
    venue: str
    order_type: str
    status: str
    fill_price: float | None = None
    fill_size: float | None = None
    fees: float = 0.0
    message: str = ""
    created_at: datetime
    lane_id: str | None = None
    market_type: str | None = None
    strategy_family: str | None = None

    model_config = {"from_attributes": True}


class ArtifactOut(BaseModel):
    id: int
    artifact_type: str
    related_id: str
    timestamp: datetime
    status: str
    payload_summary: str

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: int
    severity: str
    category: str
    message: str
    created_at: datetime
    status: str

    model_config = {"from_attributes": True}


class PerformanceOut(BaseModel):
    id: int
    timestamp: datetime
    equity: float
    pnl_daily: float
    pnl_total: float
    drawdown: float
    position_notional: float

    model_config = {"from_attributes": True}


class ControlStateOut(BaseModel):
    mode: str
    manual_pause: bool
    no_trade: bool
    trading_mode: str
    execution_provider: str


class KrakenSurfaceOut(BaseModel):
    routing_mode: str
    active_execution_provider: str
    kraken_execution_enabled_flag: bool
    allow_real_orders: bool
    cli_command_stub: str
    note: str
    latest_order_draft: dict | None = None


class Erc8004DraftSurfacesOut(BaseModel):
    """Truthful ERC-8004 (draft) alignment — off-chain / not a compliance claim."""

    eip_draft_url: str = "https://eips.ethereum.org/EIPS/eip-8004"
    alignment: str = "draft_aligned_off_chain"
    identity_registry: str = "not_deployed_in_this_repo"
    agent_uri_effective: str | None = None
    agent_registration_url: str
    agent_registration_static_url: str
    agent_wallet_placeholder: str | None = None
    on_chain_validation_attested: bool = False
    intent_binding_scheme: str = "SHA256_canonical_intent_json"
    validation_request_hash_algorithm: str = "keccak256_for_registry_shaped_payloads"
    erc8004_dev_chain_id: int | None = None
    erc8004_identity_registry_address: str | None = None
    erc8004_onchain_agent_id: str | None = None
    erc8004_validation_registry_address: str | None = None
    erc8004_reputation_registry_address: str | None = None
    intent_eip712_mode: str = "outline_only"


class ChallengeContextOut(BaseModel):
    """Hackathon rubric alignment: Kraken path + ERC-8004 draft-aligned identity + trust signals."""

    agent_id: str
    erc8004_agent_uri_stub: str | None = None
    erc8004_draft: Erc8004DraftSurfacesOut
    policy_version: str
    intent_commitment_algorithm: str
    trust_signals: list[str]
    kraken_surface: KrakenSurfaceOut


class RubricMetricsOut(BaseModel):
    """Compact trust / evidence counts for the operator dashboard."""

    validation_artifact_count: int
    risk_full_allow_count: int
    risk_reduced_count: int
    risk_allow_or_trim_count: int
    risk_block_count: int
    risk_skip_count: int = 0
    trust_score_0_100: int
    trust_posture_label: str
    trust_score_explainer: str


class TopMarketRowOut(BaseModel):
    """Latest ingested row per benchmark symbol (Kraken or demo)."""

    symbol: str
    price: float
    bid: float | None = None
    ask: float | None = None
    source: str
    captured_at: datetime

    model_config = {"from_attributes": True}


class SafetyStripOut(BaseModel):
    """Compact source vs safety signals for judges."""

    market_data_mode: str
    market_mode_label: str
    market_data_detail: str
    execution_mode: str
    paper_safe_execution: bool
    live_trading_enabled: bool
    risk_router_active: bool
    validation_artifacts_active: bool


class AutonomousStatusOut(BaseModel):
    enabled: bool
    cadence_seconds: int
    last_cycle_at: datetime | None = None
    next_cycle_at: datetime | None = None
    next_cycle_in_seconds: int | None = None


class CycleHistoryItemOut(BaseModel):
    timestamp: datetime
    outcome: str
    verdict: str | None = None
    execution_status: str | None = None
    note: str
    lane_id: str | None = None
    lane_label: str | None = None
    detail: str | None = None  # plain-English lane-aware line
    detail_technical: str | None = None  # verdict / execution / lane id recap


class ChallengeFitOut(BaseModel):
    """Judge-facing checklist — boolean flags derived from config + session data."""

    kraken_execution_surface_aligned: bool
    erc8004_identity_hooks: bool
    erc8004_agent_registration_available: bool
    combined_submission_story: bool
    paper_safe_demo_mode: bool
    risk_router_active: bool
    validation_artifacts_active: bool


class LaneTrustSummaryOut(BaseModel):
    """Per-lane allow / reduce / block / review counts with a compact trust readout."""

    lane_id: str
    lane_label: str
    market_type: str
    allow_count: int
    reduce_count: int
    block_count: int
    review_count: int
    stand_aside_count: int = 0
    artifact_count: int = 0
    """Artifacts tied to this lane’s intents (signal/risk/intent/execution proof trail)."""
    trust_score_0_100: int
    posture_label: str
    explainer_one_liner: str


class OverviewOut(BaseModel):
    control: ControlStateOut
    challenge: ChallengeContextOut
    rubric_metrics: RubricMetricsOut
    challenge_fit: ChallengeFitOut
    safety_strip: SafetyStripOut
    autonomous: AutonomousStatusOut
    cycle_history: list[CycleHistoryItemOut]
    lane_trust: list[LaneTrustSummaryOut] = Field(default_factory=list)
    top_markets: list[TopMarketRowOut]
    latest_signal: SignalOut | None = None
    latest_risk: RiskDecisionOut | None = None
    latest_intent: IntentOut | None = None
    latest_execution: ExecutionOut | None = None
    latest_performance: PerformanceOut | None = None
    market_snapshot: dict | None = None


class ActivityItem(BaseModel):
    id: int
    kind: str
    timestamp: datetime
    summary: str
    verdict_or_status: str | None = None
    related_id: str | None = None


class KrakenSkillRunRequest(BaseModel):
    operation: str
    symbols: list[str] = Field(default_factory=lambda: ["BTCUSD", "ETHUSD", "SOLUSD"])
    lane_id: str | None = None
    starting_capital: float = 10000.0
    strategy: str = "simple_ma"
    alert_price: float | None = None
    drop_percent: float = 1.5


class KrakenSkillSessionOut(BaseModel):
    id: int
    session_type: str
    operation: str
    symbols: list[str]
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    logs: list[dict] = Field(default_factory=list)
    outputs: dict = Field(default_factory=dict)
    summary: str
    metrics: dict = Field(default_factory=dict)
    rationale: str


class LanePerformanceOut(BaseModel):
    timestamp: datetime
    equity: float
    pnl_daily: float
    pnl_total: float
    drawdown: float
    open_notional: float
    turnover: float
    allow_count: int
    reduce_count: int
    block_count: int


class TradingLaneOut(BaseModel):
    lane_id: str
    lane_label: str
    market_type: str
    strategy_family: str
    default_symbols: list[str]
    capital_allocation: float
    risk_profile: str
    cadence_seconds: int
    status: str
    last_outcome: str
    performance: dict


class LaneHistoryItemOut(BaseModel):
    intent_id: int
    created_at: datetime
    asset: str
    action: str
    requested_size: float
    approved_size: float
    risk_verdict: str
    rationale: str
    status: str


class MarketChartPointOut(BaseModel):
    t: datetime
    price: float


class CandlestickOut(BaseModel):
    t: datetime
    o: float
    h: float
    l: float
    c: float
    v: float = 0.0
    forming: bool = False


class MarketContextOut(BaseModel):
    trend: str
    momentum: str
    volatility: str
    ma_short: float
    ma_long: float
    momentum_pct_10m: float
    candle_count: int
    source: str
    what_the_bot_saw: list[str]
    trade_hint: str


class TradeMarkerOut(BaseModel):
    ts: datetime
    price: float
    kind: str
    label: str


class MarketChartPackOut(BaseModel):
    symbol: str
    interval: str = "1m"
    candles: list[CandlestickOut]
    points: list[MarketChartPointOut]
    markers: list[TradeMarkerOut]
    context: MarketContextOut | None = None


class PaperSessionOut(BaseModel):
    """Aggregated paper-trading session readout for the operator UI."""

    filled_trades: int
    blocked: int
    skipped: int = 0
    reduced: int
    review: int
    allow_full: int
    equity: float | None = None
    pnl_total: float | None = None
    pnl_daily: float | None = None
    position_notional: float | None = None
    best_win_label: str | None = None
    worst_loss_label: str | None = None
    session_story: str
