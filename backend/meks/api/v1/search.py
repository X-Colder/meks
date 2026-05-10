import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.user import User

router = APIRouter()


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    user: User = Depends(require_permission(Permission.SEARCH_EXECUTE)),
    db: AsyncSession = Depends(get_db),
):
    start_time = time.time()

    from meks.services.search_service import execute_semantic_search

    results = await execute_semantic_search(
        query=request.query,
        knowledge_base_ids=request.knowledge_base_ids,
        top_k=request.top_k,
        min_score=request.min_score,
        db=db,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    from meks.models.search_history import SearchHistory
    import json

    history = SearchHistory(
        user_id=user.id,
        query=request.query,
        knowledge_base_ids=json.dumps(request.knowledge_base_ids or []),
        result_count=len(results),
        duration_ms=duration_ms,
    )
    db.add(history)
    await db.commit()

    return SearchResponse(
        results=results,
        query=request.query,
        total=len(results),
        duration_ms=duration_ms,
    )


@router.get("/history")
async def search_history(
    user: User = Depends(require_permission(Permission.SEARCH_HISTORY)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from meks.models.search_history import SearchHistory

    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()
