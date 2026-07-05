import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.models.chunk import DocumentChunk
from meks.models.document import Document
from meks.models.reading_card import PaperReadingCard

logger = logging.getLogger(__name__)

MAX_READING_TEXT_LEN = 18000


READING_CARD_PROMPT = """你是一位医学论文精读专家。请基于以下论文全文片段，为医生生成一张可用于科研讨论、选题和引用判断的精读卡片。

要求：
- 必须基于原文证据，不要编造全文中不存在的信息。
- 如果全文片段没有提供某项信息，请明确写“原文片段未提供”。
- 每个关键判断尽量引用原文中的具体短语或数据。
- 输出 Markdown，结构清晰，适合保存为科研笔记。

请输出：
1. 研究问题
2. 研究设计
3. 样本与数据来源
4. 干预/暴露因素
5. 主要结局指标
6. 统计方法
7. 主要发现
8. 临床意义
9. 局限性
10. 是否值得精读与引用建议
11. 可引用原文证据摘录

论文标题：{title}
作者：{authors}
期刊：{journal}
DOI/PMCID：{doi}

论文全文片段：
{text}
"""


async def build_reading_card(document_id: UUID, db: AsyncSession, user_id: UUID | None = None) -> PaperReadingCard:
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise ValueError("Document not found")

    chunk_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunk_result.scalars().all()
    if chunks:
        text = "\n\n".join(chunk.content for chunk in chunks)[:MAX_READING_TEXT_LEN]
    else:
        text = doc.abstract or ""

    from meks.llm.router import get_llm_provider

    provider = get_llm_provider()
    prompt = READING_CARD_PROMPT.format(
        title=doc.title,
        authors=doc.authors or "Unknown",
        journal=doc.journal or "Unknown",
        doi=doc.doi or "Unknown",
        text=text,
    )
    content = await provider.completion(prompt)

    result = await db.execute(
        select(PaperReadingCard).where(PaperReadingCard.document_id == document_id)
    )
    card = result.scalar_one_or_none()
    if card is None:
        card = PaperReadingCard(document_id=document_id, content=content, generated_by=user_id)
        db.add(card)
    else:
        card.content = content
        card.generated_by = user_id

    await db.commit()
    await db.refresh(card)
    return card
