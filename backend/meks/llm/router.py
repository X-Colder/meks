from meks.config import settings
from meks.llm.base import LLMProvider
from meks.llm.ollama_provider import OllamaProvider


def get_llm_provider(knowledge_base_ids: list[str] | None = None) -> LLMProvider:
    if settings.anthropic_api_key or settings.openai_api_key:
        from meks.llm.cloud_provider import CloudProvider
        return CloudProvider()

    return OllamaProvider()
