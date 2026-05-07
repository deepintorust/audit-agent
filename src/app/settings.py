from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="audit-agent")
    app_env: str = Field(default="dev")
    app_log_level: str = Field(default="INFO")

    # MySQL
    mysql_host: str = Field(default="mysql", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="audit", alias="MYSQL_USER")
    mysql_password: str = Field(default="audit", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="audit_agent", alias="MYSQL_DATABASE")

    # RabbitMQ
    rabbitmq_host: str = Field(default="rabbitmq", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_vhost: str = Field(default="/", alias="RABBITMQ_VHOST")

    # Qdrant
    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="audit_chunks", alias="QDRANT_COLLECTION")

    # S3-compatible storage
    storage_backend: str = Field(default="s3", alias="STORAGE_BACKEND")  # s3|local
    s3_endpoint_url: str = Field(default="http://rustfs:9000", alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(default="rustfsadmin", alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(default="rustfsadmin", alias="S3_SECRET_ACCESS_KEY")
    s3_bucket: str = Field(default="audit-files", alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    # Classification mapping
    classification_mapping_path: str = Field(
        default="/etc/audit-agent/classification.yaml",
        alias="CLASSIFICATION_MAPPING_PATH",
    )

    # LLM gateway (reuse existing llm_gateway env keys)
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_api_base: str = Field(default="", alias="LLM_API_BASE")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    vlm_model: str = Field(default="", alias="VLM_MODEL")
    llm_timeout: int = Field(default=120, alias="LLM_TIMEOUT")

    # Pipeline controls
    llm_max_concurrency: int = Field(default=8, alias="LLM_MAX_CONCURRENCY")
    embed_max_concurrency: int = Field(default=16, alias="EMBED_MAX_CONCURRENCY")
    embed_batch_size: int = Field(default=64, alias="EMBED_BATCH_SIZE")
    embed_dim: int = Field(default=1024, alias="EMBED_DIM")
    embed_model_path: str = Field(default="/models/bge-m3", alias="EMBED_MODEL_PATH")
    embed_device: str | None = Field(default=None, alias="EMBED_DEVICE")  # "cuda:0" | "cpu" | None(auto)
    embed_use_fp16: bool = Field(default=True, alias="EMBED_USE_FP16")
    embed_use_bf16: bool = Field(default=False, alias="EMBED_USE_BF16")
    embed_max_length: int = Field(default=512, alias="EMBED_MAX_LENGTH")
    max_retry_attempts: int = Field(default=6, alias="MAX_RETRY_ATTEMPTS")

    # Prompts (allow runtime override via env without rebuilding images)
    extract_prompt_template_path: str | None = Field(default=None, alias="EXTRACT_PROMPT_TEMPLATE_PATH")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
