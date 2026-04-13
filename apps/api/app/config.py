from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = Field(default="veritrade", alias="PROJECT_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    veritrade_api_port: int = Field(alias="VERITRADE_API_PORT")
    veritrade_web_port: int = Field(default=34110, alias="VERITRADE_WEB_PORT")
    veritrade_api_base_url: str = Field(alias="VERITRADE_API_BASE_URL")
    veritrade_web_base_url: str = Field(alias="VERITRADE_WEB_BASE_URL")

    database_url: str = Field(alias="DATABASE_URL")

    trading_mode: str = Field(default="paper", alias="TRADING_MODE")
    execution_provider: str = Field(default="paper", alias="EXECUTION_PROVIDER")
    enable_live_trading: bool = Field(default=False, alias="ENABLE_LIVE_TRADING")
    allow_real_orders: bool = Field(default=False, alias="ALLOW_REAL_ORDERS")
    enable_kraken_execution: bool = Field(default=False, alias="ENABLE_KRAKEN_EXECUTION")
    kraken_cli_surface_enabled: bool = Field(default=True, alias="KRAKEN_CLI_SURFACE_ENABLED")
    kraken_cli_command_stub: str = Field(default="kraken", alias="KRAKEN_CLI_COMMAND_STUB")

    veritrade_agent_id: str = Field(default="veritrade-agent-demo", alias="VERITRADE_AGENT_ID")
    erc8004_agent_uri_stub: str = Field(default="", alias="ERC8004_AGENT_URI_STUB")
    # Placeholder only — not a verified agentWallet on any Identity Registry.
    veritrade_agent_wallet_placeholder: str = Field(default="", alias="VERITRADE_AGENT_WALLET_PLACEHOLDER")

    # Local Anvil / dev-chain registry binding (optional). When both identity + agent id are set,
    # `GET /challenge/agent-registration` includes `registrations[]` pointing at the minted identity.
    erc8004_dev_chain_id: int = Field(default=31337, alias="ERC8004_DEV_CHAIN_ID")
    erc8004_identity_registry_address: str = Field(default="", alias="ERC8004_IDENTITY_REGISTRY_ADDRESS")
    erc8004_onchain_agent_id: str = Field(default="", alias="ERC8004_ONCHAIN_AGENT_ID")
    erc8004_validation_registry_address: str = Field(default="", alias="ERC8004_VALIDATION_REGISTRY_ADDRESS")
    erc8004_reputation_registry_address: str = Field(default="", alias="ERC8004_REPUTATION_REGISTRY_ADDRESS")
    # Optional JSON-RPC for read-only / ERC-1271 eth_call checks (Anvil / testnet). Not used by trading loop.
    erc8004_rpc_url: str = Field(default="", alias="ERC8004_RPC_URL")

    # Optional: emit validationRequest txs when selected artifact types are written (off by default; never blocks writes).
    erc8004_artifact_validation_emit_enabled: bool = Field(default=False, alias="ERC8004_ARTIFACT_VALIDATION_EMIT_ENABLED")
    erc8004_artifact_validation_trigger_types: str = Field(
        default="execution,lane_execution",
        alias="ERC8004_ARTIFACT_VALIDATION_TRIGGER_TYPES",
        description="Comma-separated artifact_type values that may trigger validationRequest when emit is enabled.",
    )
    erc8004_artifact_validation_private_key: str = Field(default="", alias="ERC8004_ARTIFACT_VALIDATION_PRIVATE_KEY")
    erc8004_artifact_validation_registry_address: str = Field(
        default="",
        alias="ERC8004_ARTIFACT_VALIDATION_REGISTRY_ADDRESS",
        description="When set, overrides ERC8004_VALIDATION_REGISTRY_ADDRESS for artifact-driven validationRequest txs.",
    )
    erc8004_artifact_validation_validator_address: str = Field(
        default="", alias="ERC8004_ARTIFACT_VALIDATION_VALIDATOR_ADDRESS"
    )

    # Optional second ERC-1271 verifying contract (same digest + signature) for GET /intents/{id}/signature-verification.
    veritrade_eip1271_secondary_verifier: str = Field(default="", alias="VERITRADE_EIP1271_SECONDARY_VERIFIER")

    # EIP-712 trade intent signing (optional, local dev). Never commit a real private key.
    veritrade_intent_eip712_domain_name: str = Field(default="VeriTrade", alias="VERITRADE_INTENT_EIP712_DOMAIN_NAME")
    veritrade_intent_eip712_domain_version: str = Field(default="1", alias="VERITRADE_INTENT_EIP712_DOMAIN_VERSION")
    veritrade_intent_eip712_verifying_contract: str = Field(default="", alias="VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT")
    veritrade_intent_signer_private_key: str = Field(default="", alias="VERITRADE_INTENT_SIGNER_PRIVATE_KEY")

    default_symbol: str = Field(default="BTCUSD", alias="DEFAULT_SYMBOL")
    # demo = synthetic tape; kraken_public = Kraken /public/Ticker over HTTPS; kraken_cli = external Kraken CLI binary.
    market_data_mode: str = Field(default="demo", alias="MARKET_DATA_MODE")
    # Binary used for CLI market pulls in MARKET_DATA_MODE=kraken_cli.
    kraken_market_cli_bin: str = Field(default="kraken", alias="KRAKEN_MARKET_CLI_BIN")
    # Command template must output JSON. Supports {pair}. Example:
    # KRAKEN_MARKET_CLI_TICKER_TEMPLATE=kraken public ticker --pair {pair} --json
    kraken_market_cli_ticker_template: str = Field(default="", alias="KRAKEN_MARKET_CLI_TICKER_TEMPLATE")
    default_starting_equity: float = Field(default=10000.0, alias="DEFAULT_STARTING_EQUITY")
    default_max_position_notional: float = Field(default=500.0, alias="DEFAULT_MAX_POSITION_NOTIONAL")
    default_max_daily_loss: float = Field(default=250.0, alias="DEFAULT_MAX_DAILY_LOSS")
    default_max_drawdown: float = Field(default=500.0, alias="DEFAULT_MAX_DRAWDOWN")
    default_confidence_threshold: float = Field(default=0.55, alias="DEFAULT_CONFIDENCE_THRESHOLD")

    artifacts_dir: str = Field(default="./artifacts", alias="ARTIFACTS_DIR")
    data_dir: str = Field(default="./data", alias="DATA_DIR")

    policy_version: str = "v1"

    # When false, the background autonomous runner thread is not started (avoids SQLite contention in pytest).
    veritrade_autonomous_runner: bool = Field(default=True, alias="VERITRADE_AUTONOMOUS_RUNNER")


@lru_cache
def get_settings() -> Settings:
    return Settings()
