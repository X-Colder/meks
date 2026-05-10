from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.models.chunk import DocumentChunk
from meks.models.document import Document
from meks.models.knowledge_base import KnowledgeBase
from meks.vectordb.operations import search_vectors
from meks.pipeline.embedders.local_embedder import generate_embeddings


async def execute_semantic_search(
    query: str,
    knowledge_base_ids: list[str] | None,
    top_k: int,
    min_score: float,
    db: AsyncSession,
) -> list[dict]:
    query_embedding = generate_embeddings([query])[0]

    results = []

    if not knowledge_base_ids:
        kb_result = await db.execute(select(KnowledgeBase))
        kbs = kb_result.scalars().all()
    else:
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id.in_([UUID(kid) for kid in knowledge_base_ids])
            )
        )
        kbs = kb_result.scalars().all()

    for kb in kbs:
        try:
            hits = search_vectors(
                collection_name=kb.milvus_collection,
                query_embedding=query_embedding,
                top_k=top_k,
            )
            for hit in hits:
                if hit["score"] >= min_score:
                    results.append({**hit, "knowledge_base_id": str(kb.id)})
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:top_k]

    enriched = []
    for r in results:
        doc_result = await db.execute(
            select(Document).where(Document.id == UUID(r["document_id"]))
        )
        doc = doc_result.scalar_one_or_none()
        enriched.append({
            "document_id": r["document_id"],
            "document_title": doc.title if doc else "Unknown",
            "chunk_content": r["content"],
            "score": r["score"],
            "page_number": None,
            "section_title": None,
            "authors": doc.authors if doc else None,
            "journal": doc.journal if doc else None,
        })

    return enriched
