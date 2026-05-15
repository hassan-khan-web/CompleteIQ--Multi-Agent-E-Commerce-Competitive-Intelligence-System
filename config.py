"""Configuration management for CompleteIQ system."""

import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv


load_dotenv()


class SystemConfig(BaseModel):
    """System configuration with validation."""

    # OpenAI Configuration
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = Field(default="gpt-4")
    embedding_model: str = Field(default="text-embedding-3-small")

    # Langfuse Configuration
    langfuse_public_key: str = Field(default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY", ""))
    langfuse_secret_key: str = Field(default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY", ""))
    langfuse_host: str = Field(
        default_factory=lambda: os.getenv("LANGFUSE_HOST", "https://jp.cloud.langfuse.com")
    )
    enable_tracing: bool = Field(default=True)

    # Data Configuration
    data_dir: str = Field(default="./datasets/ecommerce/")
    chroma_db_path: str = Field(default="./chroma_db/")
    chroma_collection: str = Field(default="products")

    # Processing Configuration
    batch_size: int = Field(default=128, ge=1, le=256)
    embedding_batch_size: int = Field(default=128, ge=1, le=256)
    timeout: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=1, le=10)

    # Search Configuration
    search_top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_to_file: bool = Field(default=False)
    log_file: str = Field(default="./logs/system.log")

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v:
            raise ValueError("OPENAI_API_KEY must be set")
        if not v.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        return v

    @field_validator("openai_model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        valid_models = {"gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"}
        if v not in valid_models:
            raise ValueError(f"Model must be one of {valid_models}")
        return v

    @field_validator("chroma_db_path")
    @classmethod
    def validate_chroma_path(cls, v: str) -> str:
        os.makedirs(v, exist_ok=True)
        return v

    @field_validator("log_file")
    @classmethod
    def validate_log_file(cls, v: str) -> str:
        os.makedirs(os.path.dirname(v), exist_ok=True)
        return v

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_config(config_path: Optional[str] = None) -> SystemConfig:
    """Load system configuration from environment or file.
    
    Args:
        config_path: Optional path to .env file
        
    Returns:
        Validated SystemConfig instance
    """
    if config_path:
        load_dotenv(config_path)
    else:
        load_dotenv()
    
    return SystemConfig()


def validate_config(config: SystemConfig) -> tuple[bool, list[str]]:
    """Validate all configuration requirements.
    
    Args:
        config: SystemConfig instance to validate
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check API keys
    if not config.openai_api_key:
        errors.append("OPENAI_API_KEY not configured")

    # Check paths
    if not os.path.exists(config.data_dir):
        errors.append(f"Data directory does not exist: {config.data_dir}")

    # Check Tracing configuration
    if config.enable_tracing:
        if not config.langfuse_public_key:
            errors.append("LANGFUSE_PUBLIC_KEY not configured")
        if not config.langfuse_secret_key:
            errors.append("LANGFUSE_SECRET_KEY not configured")

    return len(errors) == 0, errors
