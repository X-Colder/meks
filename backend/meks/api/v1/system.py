from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.document import Document, DocumentStatus
from meks.models.knowledge_base import KnowledgeBase
from meks.models.user import User

router = APIRouter()


@router.get("/stats")
async def system_stats(
    user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
    db: AsyncSession = Depends(get_db),
):
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    kb_count = (await db.execute(select(func.count(KnowledgeBase.id)))).scalar() or 0
    indexed_count = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == DocumentStatus.indexed)
        )
    ).scalar() or 0

    return {
        "users": user_count,
        "documents": doc_count,
        "knowledge_bases": kb_count,
        "indexed_documents": indexed_count,
    }


@router.get("/health")
async def detailed_health():
    checks = {}

    try:
        from meks.models.base import engine
        async with engine.connect() as conn:
            await conn.execute(select(1))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    try:
        from meks.vectordb.client import get_milvus_client
        client = get_milvus_client()
        checks["milvus"] = "ok" if client else "not initialized"
    except Exception as e:
        checks["milvus"] = f"error: {e}"

    return {"status": "ok" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}
