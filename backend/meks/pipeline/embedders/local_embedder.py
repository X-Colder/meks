import logging

import httpx

from meks.config import settings

logger = logging.getLogger(__name__)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    try:
        return _embed_vllm(texts)
    except Exception as e:
        logger.warning("vLLM embed unavailable (%s: %s), falling back to cloud", e.__class__.__name__, e)
        return _embed_cloud(texts)


def _embed_vllm(texts: list[str]) -> list[list[float]]:
    embeddings = []
    batch_size = settings.embedding_batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = httpx.post(
            f"{settings.vllm_embed_url}/v1/embeddings",
            json={"model": settings.embedding_model, "input": batch},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        embeddings.extend([item["embedding"] for item in sorted_data])

    return embeddings


def _embed_cloud(texts: list[str]) -> list[list[float]]:
    api_base = settings.effective_embed_api_base
    api_key = settings.effective_embed_api_key
    if not api_base and settings.effective_openai_api_key:
        api_base = "https://api.openai.com"
    model = settings.embed_model
    if not model:
        model = "text-embedding-3-large" if "api.openai.com" in (api_base or "") else settings.embedding_model

    if not api_base or not api_key:
        raise RuntimeError(
            "无可用嵌入服务：请配置 MEKS_EMBED_API_BASE/MEKS_EMBED_API_KEY，"
            "或设置 OPENAI_API_KEY/CODEX_API_KEY"
        )

    truncated = [t[:500] for t in texts]

    embeddings = []
    batch_size = 4

    for i in range(0, len(truncated), batch_size):
        batch = truncated[i : i + batch_size]
        payload = {"model": model, "input": batch}
        if model.startswith("text-embedding-3"):
            payload["dimensions"] = settings.embedding_dimension
        response = httpx.post(
            f"{api_base}/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        embeddings.extend([item["embedding"] for item in sorted_data])

    return embeddings
