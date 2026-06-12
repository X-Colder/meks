import logging

import httpx

from meks.config import settings
from meks.llm.base import LLMProvider
from meks.llm.vllm_provider import VllmProvider

logger = logging.getLogger(__name__)


def _is_vllm_available() -> bool:
    try:
        resp = httpx.get(f"{settings.vllm_chat_url}/health", timeout=2.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def get_llm_provider(knowledge_base_ids: list[str] | None = None) -> LLMProvider:
    mode = settings.llm_provider

    if mode == "local":
        if _is_vllm_available():
            return VllmProvider()
        raise RuntimeError("本地 vLLM 未运行，且配置为仅使用本地模式")

    if mode == "cloud":
        from meks.llm.cloud_provider import CloudProvider
        return CloudProvider()

    cloud_key = settings.effective_cloud_api_key
    if cloud_key:
        from meks.llm.cloud_provider import CloudProvider
        return CloudProvider()
    if _is_vllm_available():
        return VllmProvider()
    raise RuntimeError("无可用 LLM：在线 API 未配置且本地 vLLM 未运行")
