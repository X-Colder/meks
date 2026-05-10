from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.documents import DocumentListResponse, DocumentResponse
from meks.core.rbac import Permission
from meks.dependencies import get_current_user, require_permission
from meks.models.base import get_db
from meks.models.document import Document, DocumentStatus, FileType
from meks.models.user import User

router = APIRouter()

ALLOWED_EXTENSIONS = {
    "pdf": FileType.pdf,
    "docx": FileType.docx,
    "doc": FileType.doc,
    "xml": FileType.xml,
    "txt": FileType.txt,
    "md": FileType.markdown,
}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    knowledge_base_id: str = Form(...),
    title: str | None = Form(None),
    user: User = Depends(require_permission(Permission.DOC_UPLOAD)),
    db: AsyncSession = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        from meks.core.exceptions import MeksException
        raise MeksException(400, f"不支持的文件格式: {ext}")

    from meks.storage.client import upload_file
    storage_path = await upload_file(file, knowledge_base_id)

    doc = Document(
        title=title or file.filename or "未命名文档",
        filename=file.filename or "unknown",
        file_type=ALLOWED_EXTENSIONS[ext],
        file_size_bytes=file.size or 0,
        storage_path=storage_path,
        status=DocumentStatus.uploaded,
        knowledge_base_id=UUID(knowledge_base_id),
        uploaded_by=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    from meks.pipeline.tasks import process_document
    process_document.delay(str(doc.id))

    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    knowledge_base_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document)
    count_query = select(func.count(Document.id))

    if knowledge_base_id:
        query = query.where(Document.knowledge_base_id == UUID(knowledge_base_id))
        count_query = count_query.where(Document.knowledge_base_id == UUID(knowledge_base_id))

    if status:
        query = query.where(Document.status == DocumentStatus(status))
        count_query = count_query.where(Document.status == DocumentStatus(status))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Document.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return DocumentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        from meks.core.exceptions import NotFoundException
        raise NotFoundException("文档")
    return doc


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        from meks.core.exceptions import NotFoundException
        raise NotFoundException("文档")
    await db.delete(doc)
    await db.commit()
    return {"detail": "文档已删除"}
