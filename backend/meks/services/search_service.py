from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.search import SearchResultItem
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
) -> list[SearchResultItem]:
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
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Search failed for KB %s: %s", kb.id, e)
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:top_k]

    # 批量查询 Document，修复 N+1
    doc_ids = list({UUID(r["document_id"]) for r in results})
    doc_map = {}
    if doc_ids:
        doc_result = await db.execute(
            select(Document).where(Document.id.in_(doc_ids))
        )
        doc_map = {str(d.id): d for d in doc_result.scalars().all()}

    enriched = []
    for r in results:
        doc = doc_map.get(r["document_id"])
        enriched.append(SearchResultItem(
            document_id=r["document_id"],
            document_title=doc.title if doc else "Unknown",
            chunk_content=r["content"],
            score=r["score"],
            page_number=None,
            section_title=None,
            authors=doc.authors if doc else None,
            journal=doc.journal if doc else None,
        ))

    return enriched
