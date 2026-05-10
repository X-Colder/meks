from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEKS_", env_file=".env")

    app_name: str = "MEKS"
    debug: bool = False
    api_prefix: str = "/api/v1"

    secret_key: str = "change-this"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    database_url: str = "postgresql+asyncpg://meks:meks@postgres:5432/meks"

    redis_url: str = "redis://redis:6379/0"

    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_collection_prefix: str = "meks"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "meksadmin"
    minio_secret_key: str = "meks_minio_password"
    minio_bucket: str = "meks-documents"
    minio_secure: bool = False

    ollama_base_url: str = "http://ollama:11434"
    embedding_model: str = "bge-large-zh-v1.5"
    chat_model: str = "qwen2.5:14b"

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
    max_upload_size_mb: int = 100

    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"


settings = Settings()
