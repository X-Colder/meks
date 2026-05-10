from pymilvus import Collection

from meks.vectordb.collections import EMBEDDING_DIM


def insert_vectors(
    collection_name: str,
    ids: list[str],
    document_ids: list[str],
    chunk_indices: list[int],
    knowledge_base_id: str,
    embeddings: list[list[float]],
    contents: list[str],
):
    collection = Collection(name=collection_name)
    data = [
        ids,
        document_ids,
        chunk_indices,
        [knowledge_base_id] * len(ids),
        embeddings,
        contents,
    ]
    collection.insert(data)
    collection.flush()


def search_vectors(
    collection_name: str,
    query_embedding: list[float],
    top_k: int = 10,
    expr: str | None = None,
) -> list[dict]:
    collection = Collection(name=collection_name)
    collection.load()

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        expr=expr,
        output_fields=["document_id", "chunk_index", "content"],
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "id": hit.id,
            "score": hit.score,
            "document_id": hit.entity.get("document_id"),
            "chunk_index": hit.entity.get("chunk_index"),
            "content": hit.entity.get("content"),
        })
    return hits


def delete_by_document(collection_name: str, document_id: str):
    collection = Collection(name=collection_name)
    collection.delete(expr=f'document_id == "{document_id}"')
