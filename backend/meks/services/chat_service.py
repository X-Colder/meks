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
        min_score=0.2,
        db=db,
    )

    source_chunks = [
        {"document_id": r.document_id, "content": r.chunk_content[:200], "score": r.score}
        for r in search_results
    ]
    yield {"type": "sources", "data": source_chunks}

    context = "\n\n---\n\n".join(
        f"[来源: {r.document_title}]\n{r.chunk_content}" for r in search_results
    )

    from meks.llm.router import get_llm_provider
    from meks.config import settings
    provider = get_llm_provider(knowledge_base_ids)

    provider_name = settings.cloud_provider if (settings.cloud_api_key or settings.anthropic_api_key or settings.openai_api_key) else "本地模型"

    rag_prompt = f"""你是一个医学知识助手。基于以下参考文献内容回答用户的问题。
如果参考文献中没有相关信息，请明确说明。回答时请引用来源。

参考文献:
{context}

用户问题: {query}

请用中文回答:"""

    async for token in provider.stream_completion(rag_prompt):
        yield {"type": "token", "data": token}

    separator = f"\n\n---\n\n## 来自 {provider_name} 的独立分析\n\n"
    yield {"type": "token", "data": separator}

    ai_prompt = f"""你是一位资深医学研究专家。请直接回答以下问题，基于你的专业知识提供全面、准确、最新的信息。不需要参考任何特定文献，直接给出你的专业分析。

问题: {query}

请用中文回答，包含以下方面（如适用）：
1. 核心概念和背景
2. 最新研究进展和方向
3. 临床应用价值
4. 未来展望"""

    async for token in provider.stream_completion(ai_prompt):
        yield {"type": "token", "data": token}

    yield {"type": "done", "data": ""}
