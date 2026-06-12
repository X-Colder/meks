from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.analytics import AnalyticsQueryRequest, AnalyticsQueryResponse
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.user import User

router = APIRouter()


@router.post("/query", response_model=AnalyticsQueryResponse)
async def analytics_query(
    request: AnalyticsQueryRequest,
    user: User = Depends(require_permission(Permission.ANALYTICS_QUERY)),
    db: AsyncSession = Depends(get_db),
):
    from meks.services.analytics_service import execute_analytics_query

    result = await execute_analytics_query(
        query=request.query,
        db=db,
        kb_ids=request.knowledge_base_ids,
    )

    return AnalyticsQueryResponse(**result)
