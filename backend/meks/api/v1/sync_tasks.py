import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.sync_tasks import (
    SyncTaskCreate,
    SyncTaskListResponse,
    SyncTaskResponse,
    SyncTaskUpdate,
)
from meks.core.exceptions import NotFoundException
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.sync_task import SyncStatus, SyncTask
from meks.models.user import User
from meks.services.sync_service import (
    create_sync_task,
    get_sync_task,
    get_sync_tasks,
)

router = APIRouter()


@router.post("", response_model=SyncTaskResponse)
async def create_task(
    request: SyncTaskCreate,
    user: User = Depends(require_permission(Permission.SYNC_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    task = await create_sync_task(
        db=db,
        name=request.name,
        source_type=request.source_type,
        config=request.config,
        cron_expr=request.cron_expr,
        target_kb_id=request.target_kb_id,
        user_id=str(user.id),
    )
    return task


@router.get("", response_model=SyncTaskListResponse)
async def list_tasks(
    kb_id: str | None = Query(None),
    user: User = Depends(require_permission(Permission.SYNC_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    tasks = await get_sync_tasks(db, kb_id=kb_id)
    return SyncTaskListResponse(items=tasks, total=len(tasks))


@router.get("/{task_id}", response_model=SyncTaskResponse)
async def get_task_detail(
    task_id: str,
    user: User = Depends(require_permission(Permission.SYNC_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    task = await get_sync_task(db, task_id)
    if not task:
        raise NotFoundException("同步任务")
    return task


@router.post("/{task_id}/run")
async def trigger_sync(
    task_id: str,
    user: User = Depends(require_permission(Permission.SYNC_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    task = await get_sync_task(db, task_id)
    if not task:
        raise NotFoundException("同步任务")
    if task.status == SyncStatus.running:
        return {"detail": "同步任务已在运行中"}

    task.status = SyncStatus.running
    await db.commit()

    from meks.pipeline.tasks import run_sync_task
    run_sync_task.delay(str(task.id))
    return {"detail": "同步任务已触发"}


@router.post("/{task_id}/pause")
async def pause_sync(
    task_id: str,
    user: User = Depends(require_permission(Permission.SYNC_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    task = await get_sync_task(db, task_id)
    if not task:
        raise NotFoundException("同步任务")

    task.status = SyncStatus.paused
    await db.commit()
    return {"detail": "同步任务已暂停"}


@router.patch("/{task_id}", response_model=SyncTaskResponse)
async def update_task(
    task_id: str,
    request: SyncTaskUpdate,
    user: User = Depends(require_permission(Permission.SYNC_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    task = await get_sync_task(db, task_id)
    if not task:
        raise NotFoundException("同步任务")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "config" and value is not None:
            setattr(task, field, json.dumps(value))
        elif field == "status" and value is not None:
            setattr(task, field, SyncStatus(value))
        else:
            setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    user: User = Depends(require_permission(Permission.SYNC_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    task = await get_sync_task(db, task_id)
    if not task:
        raise NotFoundException("同步任务")

    await db.delete(task)
    await db.commit()
    return {"detail": "同步任务已删除"}
