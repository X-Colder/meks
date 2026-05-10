import httpx

from meks.config import settings


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    embeddings = []
    batch_size = 32

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_embeddings = _embed_batch(batch)
        embeddings.extend(batch_embeddings)

    return embeddings


def _embed_batch(texts: list[str]) -> list[list[float]]:
    results = []
    for text in texts:
        response = httpx.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.embedding_model, "prompt": text},
            timeout=60.0,
        )
        response.raise_for_status()
        results.append(response.json()["embedding"])
    return results
