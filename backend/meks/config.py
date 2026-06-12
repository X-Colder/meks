import secrets
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEKS_", env_file=".env", extra="ignore")

    app_name: str = "MEKS"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # 安全：移除默认值，强制配置
    secret_key: str = ""
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # CORS：从环境变量读取，逗号分隔
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = "postgresql+asyncpg://meks:meks@postgres:5432/meks"
    # 连接池配置
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600

    redis_url: str = "redis://redis:6379/0"

    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_collection_prefix: str = "meks"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "meks-documents"
    minio_secure: bool = False

    vllm_embed_url: str = "http://vllm-embed:8001"
    vllm_chat_url: str = "http://vllm-chat:8002"
    embedding_model: str = "/models/bge-large-zh-v1.5"
    chat_model: str = "/models/Qwen2.5-14B-Instruct"
    embedding_batch_size: int = 64

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    codex_api_key: str | None = None
    openai_api_key_env: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    codex_api_key_env: str | None = Field(default=None, validation_alias="CODEX_API_KEY")
    openai_base_url_env: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_model_env: str | None = Field(default=None, validation_alias="OPENAI_MODEL")
    openai_wire_api_env: str | None = Field(default=None, validation_alias="OPENAI_WIRE_API")

    llm_provider: str = "auto"
    cloud_provider: str = "openai"
    cloud_api_key: str | None = None
    cloud_api_base: str | None = None
    cloud_model: str | None = None
    cloud_wire_api: str | None = None

    embed_api_base: str | None = None
    embed_api_key: str | None = None
    embed_model: str | None = None
    embedding_dimension: int = 1024

    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
    max_upload_size_mb: int = 100

    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # API 限流
    rate_limit_per_minute: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @staticmethod
    def _first_non_empty(*values: Any) -> str | None:
        for value in values:
            if value is None:
                continue
            value = str(value).strip()
            if value:
                return value
        return None

    @staticmethod
    def _normalize_api_base(api_base: str) -> str:
        api_base = api_base.rstrip("/")
        return api_base.removesuffix("/v1")

    @property
    def effective_openai_api_key(self) -> str | None:
        return self._first_non_empty(
            self.codex_api_key,
            self.openai_api_key,
            self.codex_api_key_env,
            self.openai_api_key_env,
        )

    @property
    def effective_cloud_api_key(self) -> str | None:
        if self.cloud_provider == "anthropic":
            provider_key = self.anthropic_api_key
        else:
            provider_key = self.effective_openai_api_key
        return self._first_non_empty(self.cloud_api_key, provider_key)

    @property
    def effective_cloud_api_base(self) -> str | None:
        api_base = self._first_non_empty(
            self.cloud_api_base,
            self.openai_base_url_env if self.cloud_provider != "anthropic" else None,
        )
        return self._normalize_api_base(api_base) if api_base else None

    @property
    def effective_cloud_model(self) -> str | None:
        return self._first_non_empty(
            self.cloud_model,
            self.openai_model_env if self.cloud_provider != "anthropic" else None,
        )

    @property
    def effective_cloud_wire_api(self) -> str:
        return (
            self._first_non_empty(
                self.cloud_wire_api,
                self.openai_wire_api_env if self.cloud_provider != "anthropic" else None,
            )
            or "chat"
        ).lower()

    @property
    def effective_embed_api_key(self) -> str | None:
        return self._first_non_empty(
            self.embed_api_key,
            self.cloud_api_key,
            self.effective_openai_api_key,
        )

    @property
    def effective_embed_api_base(self) -> str | None:
        api_base = self._first_non_empty(
            self.embed_api_base,
            self.cloud_api_base,
            self.openai_base_url_env,
        )
        return self._normalize_api_base(api_base) if api_base else None


settings = Settings()

# 启动校验
if not settings.secret_key or settings.secret_key in ("change-this", ""):
    if settings.debug:
        settings.secret_key = "dev-only-insecure-key-" + secrets.token_hex(16)
    else:
        raise RuntimeError("MEKS_SECRET_KEY must be set in production!")
