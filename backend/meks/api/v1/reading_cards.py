from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.reading_cards import ReadingCardResponse, ReadingCardUpsert
from meks.core.exceptions import NotFoundException
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.document import Document
from meks.models.reading_card import PaperReadingCard
from meks.models.user import User

router = APIRouter()


async def _ensure_document(document_id: str, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundException("文档")
    return doc


@router.get("/{document_id}", response_model=ReadingCardResponse)
async def get_reading_card(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_document(document_id, db)
    result = await db.execute(
        select(PaperReadingCard).where(PaperReadingCard.document_id == UUID(document_id))
    )
    card = result.scalar_one_or_none()
    if not card:
        raise NotFoundException("精读卡片")
    return card


@router.put("/{document_id}", response_model=ReadingCardResponse)
async def save_reading_card(
    document_id: str,
    request: ReadingCardUpsert,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_document(document_id, db)
    result = await db.execute(
        select(PaperReadingCard).where(PaperReadingCard.document_id == UUID(document_id))
    )
    card = result.scalar_one_or_none()
    if card is None:
        card = PaperReadingCard(
            document_id=UUID(document_id),
            content=request.content,
            generated_by=user.id,
        )
        db.add(card)
    else:
        card.content = request.content
        card.generated_by = user.id
    await db.commit()
    await db.refresh(card)
    return card


@router.post("/{document_id}/generate", status_code=202)
async def trigger_reading_card(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_document(document_id, db)
    from meks.pipeline.tasks import generate_reading_card_task

    generate_reading_card_task.delay(document_id, str(user.id))
    return {"detail": "精读卡片生成任务已提交", "document_id": document_id}
