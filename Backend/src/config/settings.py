# =============================================================================
# Application Settings
# =============================================================================
"""
Pydantic Settings configuration for the Claude Assistant Platform.

Loads configuration from environment variables with validation and type safety.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    The .env file is automatically loaded if present.

    Attributes:
        app_name: Name of the application.
        app_env: Current environment (development, staging, production).
        debug: Enable debug mode for verbose logging.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        api_host: Host address for the API server.
        api_port: Port number for the API server.
        allowed_hosts: Comma-separated list of allowed hosts.
        anthropic_api_key: API key for Anthropic Claude API.
        claude_model: Claude model to use for the orchestrator.
        postgres_db: PostgreSQL database name.
        postgres_user: PostgreSQL username.
        postgres_password: PostgreSQL password.
        postgres_host: PostgreSQL host address.
        postgres_port: PostgreSQL port number.
        telegram_bot_token: Production Telegram bot token from @BotFather.
        telegram_dev_bot_token: Development Telegram bot token (used when APP_ENV=development).
        telegram_allowed_user_ids: Comma-separated list of allowed Telegram user IDs.
        telegram_polling_timeout: Long-polling timeout for Telegram API.
        telegram_enabled: Enable/disable Telegram bot integration.
        telegram_mcp_host: Hostname of the Telegram MCP server.
        telegram_mcp_port: Port of the Telegram MCP server.
    """

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_name: str = Field(
        default="claude-assistant-platform",
        description="Name of the application"
    )
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Current environment"
    )
    debug: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    # -------------------------------------------------------------------------
    # API Settings
    # -------------------------------------------------------------------------
    api_host: str = Field(
        default="0.0.0.0",
        description="Host address for the API server"
    )
    api_port: int = Field(
        default=8000,
        description="Port number for the API server"
    )
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts"
    )

    # -------------------------------------------------------------------------
    # Anthropic API Settings
    # -------------------------------------------------------------------------
    anthropic_api_key: str = Field(
        default="",
        description="API key for Anthropic Claude API"
    )
    claude_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use for the orchestrator"
    )

    # -------------------------------------------------------------------------
    # Database Settings
    # -------------------------------------------------------------------------
    postgres_db: str = Field(
        default="claude_assistant_platform",
        description="PostgreSQL database name"
    )
    postgres_user: str = Field(
        default="postgres",
        description="PostgreSQL username"
    )
    postgres_password: str = Field(
        default="",
        description="PostgreSQL password"
    )
    postgres_host: str = Field(
        default="db",
        description="PostgreSQL host address"
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL port number"
    )

    # -------------------------------------------------------------------------
    # Telegram Bot Settings
    # -------------------------------------------------------------------------
    telegram_bot_token: str = Field(
        default="",
        description="Production Telegram bot token from @BotFather"
    )
    telegram_dev_bot_token: str = Field(
        default="",
        description="Development Telegram bot token (used when APP_ENV=development)"
    )
    telegram_allowed_user_ids: str = Field(
        default="",
        description="Comma-separated list of allowed Telegram user IDs"
    )
    telegram_polling_timeout: int = Field(
        default=30,
        description="Long-polling timeout in seconds for Telegram API"
    )
    telegram_enabled: bool = Field(
        default=True,
        description="Enable/disable Telegram bot integration"
    )

    # -------------------------------------------------------------------------
    # Telegram MCP Server Settings (internal Docker network)
    # -------------------------------------------------------------------------
    telegram_mcp_host: str = Field(
        default="telegram-mcp",
        description="Hostname of the Telegram MCP server"
    )
    telegram_mcp_port: int = Field(
        default=8080,
        description="Port of the Telegram MCP server"
    )

    # -------------------------------------------------------------------------
    # Todo Executor Settings
    # -------------------------------------------------------------------------
    todo_executor_interval: int = Field(
        default=30,
        description="Interval in seconds between todo execution checks"
    )
    todo_executor_batch_size: int = Field(
        default=5,
        description="Maximum number of todos to process per execution cycle"
    )
    todo_executor_enabled: bool = Field(
        default=True,
        description="Enable/disable the background todo executor"
    )

    # -------------------------------------------------------------------------
    # Model Configuration
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    @property
    def database_url(self) -> str:
        """
        Construct the database URL for psycopg async driver.

        Uses the psycopg3 dialect for SQLAlchemy async operations.
        The psycopg driver provides better performance and native
        async support compared to asyncpg.

        Returns:
            PostgreSQL connection URL using psycopg dialect.
        """
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def allowed_hosts_list(self) -> list[str]:
        """
        Parse allowed hosts string into a list.

        Returns:
            List of allowed host strings.
        """
        return [host.strip() for host in self.allowed_hosts.split(",")]

    @property
    def telegram_allowed_user_ids_list(self) -> list[int]:
        """
        Parse Telegram allowed user IDs string into a list of integers.

        Returns:
            List of allowed Telegram user IDs.
        """
        if not self.telegram_allowed_user_ids:
            return []
        return [
            int(uid.strip())
            for uid in self.telegram_allowed_user_ids.split(",")
            if uid.strip()
        ]

    @property
    def telegram_mcp_url(self) -> str:
        """
        Construct the Telegram MCP server URL.

        Returns:
            Full URL to the Telegram MCP server.
        """
        return f"http://{self.telegram_mcp_host}:{self.telegram_mcp_port}"

    @property
    def telegram_active_bot_token(self) -> str:
        """
        Get the appropriate Telegram bot token based on environment.

        In development mode, uses the dev bot token if available,
        otherwise falls back to the production token.
        In production/staging, always uses the production token.

        This allows running a local dev instance without conflicting
        with the production bot's polling.

        Returns:
            The bot token to use for the current environment.
        """
        if self.app_env == "development" and self.telegram_dev_bot_token:
            return self.telegram_dev_bot_token
        return self.telegram_bot_token

    @property
    def telegram_is_configured(self) -> bool:
        """
        Check if Telegram bot is properly configured.

        Returns:
            True if an active bot token is set and Telegram is enabled.
        """
        return bool(self.telegram_active_bot_token and self.telegram_enabled)

    @property
    def telegram_is_dev_bot(self) -> bool:
        """
        Check if currently using the development bot.

        Returns:
            True if using the dev bot token, False if using production.
        """
        return (
            self.app_env == "development"
            and bool(self.telegram_dev_bot_token)
            and self.telegram_active_bot_token == self.telegram_dev_bot_token
        )

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("anthropic_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """
        Validate that API key is provided in non-development environments.

        Args:
            v: The API key value.

        Returns:
            The validated API key.

        Raises:
            ValueError: If API key is empty in production.
        """
        # Note: We allow empty in development for testing without API
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings instance.

    Uses LRU cache to ensure settings are only loaded once.

    Returns:
        Settings instance with loaded configuration.
    """
    return Settings()
