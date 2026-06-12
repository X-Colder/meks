from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.medical_records import MedicalRecordListResponse, MedicalRecordResponse
from meks.core.exceptions import NotFoundException
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.document import Document
from meks.models.medical_record import MedicalRecord
from meks.models.user import User

router = APIRouter()


@router.get("", response_model=MedicalRecordListResponse)
async def list_medical_records(
    knowledge_base_id: str | None = None,
    severity: str | None = None,
    department: str | None = None,
    icd10_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    query = select(MedicalRecord)
    count_query = select(func.count(MedicalRecord.id))

    if knowledge_base_id:
        query = query.join(Document, MedicalRecord.document_id == Document.id).where(
            Document.knowledge_base_id == UUID(knowledge_base_id)
        )
        count_query = count_query.join(Document, MedicalRecord.document_id == Document.id).where(
            Document.knowledge_base_id == UUID(knowledge_base_id)
        )
    if severity:
        query = query.where(MedicalRecord.severity == severity)
        count_query = count_query.where(MedicalRecord.severity == severity)
    if department:
        query = query.where(MedicalRecord.department == department)
        count_query = count_query.where(MedicalRecord.department == department)
    if icd10_code:
        query = query.where(MedicalRecord.icd10_code == icd10_code)
        count_query = count_query.where(MedicalRecord.icd10_code == icd10_code)
    if date_from:
        dt_from = datetime.fromisoformat(date_from).date()
        query = query.where(MedicalRecord.admission_date >= dt_from)
        count_query = count_query.where(MedicalRecord.admission_date >= dt_from)
    if date_to:
        dt_to = datetime.fromisoformat(date_to).date()
        query = query.where(MedicalRecord.admission_date <= dt_to)
        count_query = count_query.where(MedicalRecord.admission_date <= dt_to)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(MedicalRecord.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return MedicalRecordListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record(
    record_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise NotFoundException("病历记录")
    return record


@router.post("/documents/{document_id}/re-extract")
async def re_extract_medical_record(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_REPROCESS)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundException("文档")

    from meks.pipeline.tasks import extract_medical_record_task
    extract_medical_record_task.delay(document_id)

    return {"detail": "病历重新提取任务已提交", "document_id": document_id}
