import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.knowledge_bases import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from meks.core.exceptions import NotFoundException
from meks.core.rbac import Permission
from meks.dependencies import get_current_user, require_permission
from meks.models.base import get_db
from meks.models.knowledge_base import KnowledgeBase, Visibility
from meks.models.user import User

router = APIRouter()


@router.post("", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    user: User = Depends(require_permission(Permission.KB_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    collection_name = f"meks_kb_{uuid.uuid4().hex[:12]}"
    kb = KnowledgeBase(
        name=request.name,
        description=request.description,
        owner_id=user.id,
        visibility=Visibility(request.visibility),
        department=request.department or user.department,
        milvus_collection=collection_name,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    from meks.vectordb.collections import create_collection
    create_collection(collection_name)

    return kb


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    user: User = Depends(require_permission(Permission.KB_READ)),
    db: AsyncSession = Depends(get_db),
):
    query = select(KnowledgeBase).where(
        (KnowledgeBase.visibility == Visibility.public)
        | (KnowledgeBase.owner_id == user.id)
        | (KnowledgeBase.department == user.department)
    )
    result = await db.execute(query.order_by(KnowledgeBase.created_at.desc()))
    return result.scalars().all()


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    user: User = Depends(require_permission(Permission.KB_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(kb_id))
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundException("知识库")
    return kb


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdate,
    user: User = Depends(require_permission(Permission.KB_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(kb_id))
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundException("知识库")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(kb, field, value)

    await db.commit()
    await db.refresh(kb)
    return kb


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    user: User = Depends(require_permission(Permission.KB_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(kb_id))
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundException("知识库")

    from meks.vectordb.collections import drop_collection
    drop_collection(kb.milvus_collection)

    await db.delete(kb)
    await db.commit()
    return {"detail": "知识库已删除"}
