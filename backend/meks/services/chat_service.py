import json
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from meks.services.search_service import execute_semantic_search


async def generate_rag_response(
    query: str,
    knowledge_base_ids: list[str],
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    search_results = await execute_semantic_search(
        query=query,
        knowledge_base_ids=knowledge_base_ids,
        top_k=5,
        min_score=0.3,
        db=db,
    )

    source_chunks = [
        {"document_id": r["document_id"], "content": r["chunk_content"][:200], "score": r["score"]}
        for r in search_results
    ]
    yield {"type": "sources", "data": source_chunks}

    context = "\n\n---\n\n".join(
        f"[来源: {r['document_title']}]\n{r['chunk_content']}" for r in search_results
    )

    from meks.llm.router import get_llm_provider
    provider = get_llm_provider(knowledge_base_ids)

    prompt = f"""你是一个医学知识助手。基于以下参考文献内容回答用户的问题。
如果参考文献中没有相关信息，请明确说明。回答时请引用来源。

参考文献:
{context}

用户问题: {query}

请用中文回答:"""

    async for token in provider.stream_completion(prompt):
        yield {"type": "token", "data": token}

    yield {"type": "done", "data": ""}
