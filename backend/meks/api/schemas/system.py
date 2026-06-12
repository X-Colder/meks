from pydantic import BaseModel


class LLMSettingsResponse(BaseModel):
    llm_provider: str
    cloud_provider: str
    cloud_api_key_masked: str | None
    cloud_api_base: str | None
    cloud_model: str | None
    vllm_chat_url: str
    vllm_available: bool


class LLMSettingsUpdate(BaseModel):
    llm_provider: str | None = None
    cloud_provider: str | None = None
    cloud_api_key: str | None = None
    cloud_api_base: str | None = None
    cloud_model: str | None = None
