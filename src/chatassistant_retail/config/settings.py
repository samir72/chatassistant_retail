"""Application settings using Pydantic Settings."""

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Deployment configuration
    deployment_mode: Literal["hf_spaces", "local"] = Field(
        default="hf_spaces",
        description="Deployment mode: hf_spaces (Hugging Face Spaces) or local",
    )

    # Azure OpenAI configuration
    azure_openai_endpoint: str = Field(
        ...,
        description="Azure OpenAI endpoint URL",
    )
    azure_openai_api_key: str = Field(
        ...,
        description="Azure OpenAI API key",
    )
    azure_openai_deployment_name: str = Field(
        default="gpt-4o-mini",
        description="Azure OpenAI deployment name",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version",
    )
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-ada-002",
        description="Azure OpenAI embedding deployment name",
    )

    # Azure AI Search configuration
    AZURE_COGNITIVE_SEARCH_ENDPOINT: str | None = Field(
        ...,
        description="Azure AI Search endpoint URL",
    )
    AZURE_COGNITIVE_SEARCH_API_KEY: str | None = Field(
        ...,
        description="Azure AI Search API key",
    )
    azure_search_index_name: str = Field(
        default="products",
        description="Azure AI Search index name",
    )

    # LangFuse observability configuration
    langfuse_enabled: bool = Field(
        default=True,
        description="Enable LangFuse tracing",
    )
    langfuse_public_key: str | None = Field(
        default=None,
        description="LangFuse public key",
    )
    langfuse_secret_key: str | None = Field(
        default=None,
        description="LangFuse secret key",
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="LangFuse host URL",
    )

    # Session storage configuration
    redis_url: str | None = Field(
        default=None,
        description="Redis connection URL for session storage (local mode)",
    )
    postgres_url: str | None = Field(
        default=None,
        description="PostgreSQL connection URL for session storage (local mode)",
    )

    # HuggingFace configuration
    hf_token: str | None = Field(
        default=None,
        description="HuggingFace API token",
    )

    # Application configuration
    max_conversation_history: int = Field(
        default=10,
        description="Maximum number of messages to keep in conversation history",
    )
    enable_streaming: bool = Field(
        default=True,
        description="Enable streaming responses from LLM",
    )
    cache_embeddings: bool = Field(
        default=True,
        description="Cache embeddings for frequently queried products",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL in seconds (1 hour default)",
    )

    # Sample data configuration
    sample_data_products_count: int = Field(
        default=500,
        description="Number of sample products to generate",
    )
    sample_data_sales_months: int = Field(
        default=6,
        description="Number of months of sales history to generate",
    )

    # Security configuration
    input_max_length: int = Field(
        default=1000,
        description="Maximum length for user input (security)",
    )

    @field_validator("azure_openai_api_key")
    @classmethod
    def validate_azure_key(cls, v: str) -> str:
        """Validate Azure OpenAI API key format."""
        if v.startswith("sk-"):
            logger.warning(
                "Potential OpenAI key detected instead of Azure key. Azure keys typically don't start with 'sk-'"
            )
        return v

    @field_validator("deployment_mode")
    @classmethod
    def validate_deployment_mode(cls, v: str) -> str:
        """Validate deployment mode configuration."""
        if v not in ["hf_spaces", "local"]:
            raise ValueError(f"Invalid deployment mode: {v}. Must be 'hf_spaces' or 'local'")
        return v

    def validate_required_credentials(self) -> None:
        """Validate that required credentials are present."""
        if not self.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT must be set")
        if not self.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY must be set")

        if self.langfuse_enabled:
            if not self.langfuse_public_key or not self.langfuse_secret_key:
                logger.warning("LangFuse is enabled but credentials are missing. Disabling LangFuse tracing.")
                self.langfuse_enabled = False

        if self.deployment_mode == "local":
            if not self.redis_url and not self.postgres_url:
                logger.warning(
                    "Local deployment mode requires Redis or PostgreSQL URL. Falling back to in-memory session storage."
                )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate_required_credentials()
    return settings
