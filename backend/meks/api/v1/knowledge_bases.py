import json
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.knowledge_bases import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from meks.core.exceptions import ForbiddenException, NotFoundException
from meks.core.rbac import Permission
from meks.dependencies import get_current_user, require_permission
from meks.models.base import get_db
from meks.models.knowledge_base import KnowledgeBase, KBType, Visibility
from meks.models.user import User, UserRole

router = APIRouter()


async def _get_kb_with_access_check(
    kb_id: str, user: User, db: AsyncSession, require_owner: bool = False
) -> KnowledgeBase:
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(kb_id))
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundException("知识库")

    if require_owner and kb.owner_id != user.id and user.role != UserRole.admin:
        raise ForbiddenException("只有知识库创建者或管理员可以执行此操作")

    return kb


@router.post("", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    user: User = Depends(require_permission(Permission.KB_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    collection_name = f"meks_kb_{uuid.uuid4().hex[:12]}"

    # 先创建 Milvus collection，再 commit DB，保证数据一致性
    from meks.vectordb.collections import create_collection
    create_collection(collection_name)

    try:
        kb = KnowledgeBase(
            name=request.name,
            description=request.description,
            owner_id=user.id,
            visibility=Visibility(request.visibility),
            department=request.department or user.department,
            milvus_collection=collection_name,
            kb_type=KBType(request.kb_type),
            field_template=json.dumps(request.field_template) if request.field_template is not None else None,
            crawl_config=json.dumps(request.crawl_config) if request.crawl_config is not None else None,
        )
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        return kb
    except Exception:
        from meks.vectordb.collections import drop_collection
        drop_collection(collection_name)
        raise


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    user: User = Depends(require_permission(Permission.KB_READ)),
    db: AsyncSession = Depends(get_db),
):
    conditions = [
        KnowledgeBase.visibility == Visibility.public,
        KnowledgeBase.owner_id == user.id,
    ]
    if user.department:
        conditions.append(
            (KnowledgeBase.department == user.department)
            & (KnowledgeBase.visibility == Visibility.department)
        )

    from sqlalchemy import or_
    query = select(KnowledgeBase).where(or_(*conditions))
    result = await db.execute(query.order_by(KnowledgeBase.created_at.desc()))
    kbs = result.scalars().all()

    from meks.models.document import Document
    for kb in kbs:
        count_result = await db.execute(
            select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
        )
        kb.document_count = count_result.scalar() or 0
    await db.commit()

    return kbs


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
    kb = await _get_kb_with_access_check(kb_id, user, db, require_owner=True)
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
    import logging
    kb = await _get_kb_with_access_check(kb_id, user, db, require_owner=True)

    from meks.vectordb.collections import drop_collection
    try:
        drop_collection(kb.milvus_collection)
    except Exception:
        logging.getLogger(__name__).warning(f"Failed to drop collection {kb.milvus_collection}")

    await db.delete(kb)
    await db.commit()
    return {"detail": "知识库已删除"}
