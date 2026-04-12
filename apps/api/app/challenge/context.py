from app.adapters.kraken_execution_surface import build_kraken_cli_order_draft, get_surface_status
from app.config import get_settings
from app.models import MarketSnapshot, TradeIntent
from app.schemas.api import ChallengeContextOut, KrakenSurfaceOut


def build_challenge_context(
    latest_intent: TradeIntent | None,
    latest_snap: MarketSnapshot | None,
) -> ChallengeContextOut:
    s = get_settings()
    st = get_surface_status()
    mark = float(latest_snap.price) if latest_snap else None
    draft = None
    if latest_intent is not None and mark is not None:
        draft = build_kraken_cli_order_draft(latest_intent, mark)

    kr = KrakenSurfaceOut(
        routing_mode=st.routing_mode,
        active_execution_provider=st.active_execution_provider,
        kraken_execution_enabled_flag=st.kraken_execution_enabled_flag,
        allow_real_orders=st.allow_real_orders,
        cli_command_stub=st.cli_command_stub,
        note=st.note,
        latest_order_draft=draft,
    )

    trust_signals = [
        "risk_router_verdict_before_execution",
        "signed_intent_commitment_sha256_offchain",
        "validation_artifacts_persisted_db_and_fs",
        "operator_pause_step_stop_surface",
        "paper_default_live_gated",
        "kraken_cli_order_draft_typed_surface",
    ]

    stub = (s.erc8004_agent_uri_stub or "").strip()
    return ChallengeContextOut(
        agent_id=s.veritrade_agent_id,
        erc8004_agent_uri_stub=stub or None,
        policy_version=s.policy_version,
        intent_commitment_algorithm="SHA256(canonical JSON of binding intent fields)",
        trust_signals=trust_signals,
        kraken_surface=kr,
    )
