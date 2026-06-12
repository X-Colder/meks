from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.audit_logs import AuditLogListResponse, AuditLogResponse
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.audit_log import AuditLog
from meks.models.base import get_db
from meks.models.user import User

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission(Permission.ADMIN_AUDIT)),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if user_id:
        from uuid import UUID
        query = query.where(AuditLog.user_id == UUID(user_id))
        count_query = count_query.where(AuditLog.user_id == UUID(user_id))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if date_from:
        dt_from = datetime.fromisoformat(date_from)
        query = query.where(AuditLog.created_at >= dt_from)
        count_query = count_query.where(AuditLog.created_at >= dt_from)
    if date_to:
        dt_to = datetime.fromisoformat(date_to)
        query = query.where(AuditLog.created_at <= dt_to)
        count_query = count_query.where(AuditLog.created_at <= dt_to)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)
