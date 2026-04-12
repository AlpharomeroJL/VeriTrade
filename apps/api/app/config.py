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
