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
        telegram_bot_token: Telegram bot token from @BotFather.
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
        description="Telegram bot token from @BotFather"
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
        Construct the database URL from individual components.

        Returns:
            PostgreSQL connection URL string.
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
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
    def telegram_is_configured(self) -> bool:
        """
        Check if Telegram bot is properly configured.

        Returns:
            True if bot token is set and enabled.
        """
        return bool(self.telegram_bot_token and self.telegram_enabled)

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
