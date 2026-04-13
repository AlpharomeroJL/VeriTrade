from app.adapters.kraken_execution_surface import build_kraken_cli_order_draft, get_surface_status
from app.challenge.eip712_intent import eip712_signing_configured
from app.challenge.registration import agent_registration_static_url, agent_uri_effective
from app.config import get_settings
from app.models import MarketSnapshot, TradeIntent
from app.schemas.api import ChallengeContextOut, Erc8004DraftSurfacesOut, KrakenSurfaceOut


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
        "erc8004_registration_file_exposed_api_and_well_known",
        "GET_/challenge/agent-registration/verify_same_origin_checks",
        "GET_/challenge/erc8004/onchain-read_optional_rpc_reads",
        "anvil_wallet_roles_doc_and_prove_local_slice_script",
    ]

    stub = (s.erc8004_agent_uri_stub or "").strip()
    api_base = s.veritrade_api_base_url.rstrip("/")
    wallet_ph = (s.veritrade_agent_wallet_placeholder or "").strip() or None
    id_reg = "not_deployed_from_this_repo_runtime"
    if (s.erc8004_identity_registry_address or "").strip():
        id_reg = "env_registry_address_configured_local_or_testnet_only"
    intent_mode = "local_dev_typed_signing_enabled" if eip712_signing_configured(s) else "outline_only"
    erc = Erc8004DraftSurfacesOut(
        identity_registry=id_reg,
        agent_uri_effective=agent_uri_effective(s),
        agent_registration_url=f"{api_base}/challenge/agent-registration",
        agent_registration_static_url=agent_registration_static_url(s),
        agent_wallet_placeholder=wallet_ph,
        erc8004_dev_chain_id=s.erc8004_dev_chain_id,
        erc8004_identity_registry_address=(s.erc8004_identity_registry_address or "").strip() or None,
        erc8004_onchain_agent_id=(s.erc8004_onchain_agent_id or "").strip() or None,
        erc8004_validation_registry_address=(s.erc8004_validation_registry_address or "").strip() or None,
        erc8004_reputation_registry_address=(s.erc8004_reputation_registry_address or "").strip() or None,
        intent_eip712_mode=intent_mode,
    )
    return ChallengeContextOut(
        agent_id=s.veritrade_agent_id,
        erc8004_agent_uri_stub=stub or None,
        erc8004_draft=erc,
        policy_version=s.policy_version,
        intent_commitment_algorithm="SHA256(canonical JSON of binding intent fields)",
        trust_signals=trust_signals,
        kraken_surface=kr,
    )
