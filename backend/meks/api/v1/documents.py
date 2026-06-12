from uuid import UUID

import logging

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.documents import DocumentContentResponse, DocumentListResponse, DocumentResponse
from meks.core.rbac import Permission
from meks.dependencies import get_current_user, require_permission
from meks.models.base import get_db
from meks.models.document import Document, DocumentStatus, FileType
from meks.models.knowledge_base import KnowledgeBase
from meks.models.user import User

router = APIRouter()

logger = logging.getLogger(__name__)

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


@router.post("/reindex")
async def reindex_documents(
    knowledge_base_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission(Permission.DOC_UPLOAD)),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Document)
        .where(Document.status != DocumentStatus.indexed)
        .order_by(Document.updated_at.asc())
        .limit(limit)
    )
    if knowledge_base_id:
        query = query.where(Document.knowledge_base_id == UUID(knowledge_base_id))

    result = await db.execute(query)
    docs = result.scalars().all()

    from meks.pipeline.tasks import process_document
    for doc in docs:
        doc.status = DocumentStatus.uploaded
        doc.error_message = None
        process_document.delay(str(doc.id))

    await db.commit()
    return {"detail": f"已提交 {len(docs)} 篇文档重新索引", "count": len(docs)}


@router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_UPLOAD)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        from meks.core.exceptions import NotFoundException
        raise NotFoundException("文档")

    doc.status = DocumentStatus.uploaded
    doc.error_message = None
    await db.commit()

    from meks.pipeline.tasks import process_document
    process_document.delay(str(doc.id))
    return {"detail": "文档已提交重新索引"}


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


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
async def get_document_content(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        from meks.core.exceptions import NotFoundException
        raise NotFoundException("文档")

    from meks.models.chunk import DocumentChunk
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    if chunks:
        content = "\n\n".join(c.content for c in chunks)
    else:
        from meks.storage.client import download_file
        from meks.pipeline.extractors import extract_text
        file_data = download_file(doc.storage_path)
        content, _ = extract_text(file_data, doc.file_type.value)

    return DocumentContentResponse(
        id=doc.id,
        title=doc.title,
        authors=doc.authors,
        abstract=doc.abstract,
        content=content,
        status=doc.status.value,
        publication_date=doc.publication_date,
    )


@router.post("/{document_id}/translate")
async def translate_document(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        from meks.core.exceptions import NotFoundException
        raise NotFoundException("文档")

    from meks.models.chunk import DocumentChunk
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    if chunks:
        full_text = "\n\n".join(c.content for c in chunks)
    else:
        from meks.storage.client import download_file
        from meks.pipeline.extractors import extract_text
        file_data = download_file(doc.storage_path)
        full_text, _ = extract_text(file_data, doc.file_type.value)

    from meks.llm.router import get_llm_provider
    from sse_starlette.sse import EventSourceResponse
    import json as _json

    provider = get_llm_provider()
    abstract_text = doc.abstract or ""

    segment_size = 6000
    segments = []
    for i in range(0, len(full_text), segment_size):
        segments.append(full_text[i:i + segment_size])

    async def stream_translate():
        if abstract_text:
            prompt = f"请将以下英文医学论文摘要翻译为中文，保持学术准确性，医学术语使用标准中文译名，只输出翻译结果：\n\n{abstract_text}\n\n中文翻译："
            translated = await provider.completion(prompt)
            yield {"event": "abstract", "data": _json.dumps({"content": translated}, ensure_ascii=False)}

        for idx, seg in enumerate(segments):
            prompt = f"请将以下英文医学论文内容翻译为中文（第{idx+1}/{len(segments)}段）。保持学术准确性，医学术语使用标准中文译名，保持段落结构，只输出翻译结果：\n\n{seg}\n\n中文翻译："
            translated = await provider.completion(prompt)
            yield {"event": "segment", "data": _json.dumps({"index": idx, "total": len(segments), "content": translated}, ensure_ascii=False)}

        yield {"event": "done", "data": ""}

    return EventSourceResponse(stream_translate())


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

    from meks.vectordb.operations import delete_by_document
    from meks.vectordb.collections import utility
    from meks.storage.client import get_minio_client
    from meks.config import settings

    try:
        collection_name_result = await db.execute(
            select(KnowledgeBase.milvus_collection).where(
                KnowledgeBase.id == doc.knowledge_base_id
            )
        )
        collection_name = collection_name_result.scalar_one_or_none()
        if collection_name and utility.has_collection(collection_name):
            delete_by_document(collection_name, document_id)
    except Exception as e:
        logger.warning(f"Failed to delete vectors for document {document_id}: {e}")

    try:
        client = get_minio_client()
        client.remove_object(settings.minio_bucket, doc.storage_path)
    except Exception as e:
        logger.warning(f"Failed to delete file for document {document_id}: {e}")

    await db.delete(doc)
    await db.commit()
    return {"detail": "文档已删除"}
