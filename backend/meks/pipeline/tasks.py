from celery import Celery

from meks.config import settings

celery_app = Celery(
    "meks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str):
    import asyncio
    asyncio.run(_process_document_async(document_id))


async def _process_document_async(document_id: str):
    from uuid import UUID
    from sqlalchemy import select
    from meks.models.base import async_session
    from meks.models.document import Document, DocumentStatus

    async with async_session() as db:
        result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
        doc = result.scalar_one_or_none()
        if not doc:
            return

        doc.status = DocumentStatus.processing
        await db.commit()

        try:
            from meks.pipeline.extractors import extract_text
            from meks.pipeline.chunkers.semantic_chunker import chunk_text
            from meks.pipeline.embedders.local_embedder import generate_embeddings

            from meks.storage.client import download_file
            file_data = download_file(doc.storage_path)

            text, metadata = extract_text(file_data, doc.file_type.value)

            if metadata.get("title"):
                doc.title = metadata["title"]
            if metadata.get("authors"):
                doc.authors = metadata["authors"]
            if metadata.get("abstract"):
                doc.abstract = metadata["abstract"]

            chunks = chunk_text(text)

            embeddings = generate_embeddings([c["content"] for c in chunks])

            import uuid as uuid_mod
            from meks.vectordb.operations import insert_vectors
            from meks.models.chunk import DocumentChunk

            chunk_ids = [uuid_mod.uuid4().hex for _ in chunks]
            insert_vectors(
                collection_name=await _get_collection_name(db, doc.knowledge_base_id),
                ids=chunk_ids,
                document_ids=[str(doc.id)] * len(chunks),
                chunk_indices=[c["index"] for c in chunks],
                knowledge_base_id=str(doc.knowledge_base_id),
                embeddings=embeddings,
                contents=[c["content"] for c in chunks],
            )

            for i, chunk in enumerate(chunks):
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk["index"],
                    content=chunk["content"],
                    token_count=chunk["token_count"],
                    page_number=chunk.get("page_number"),
                    section_title=chunk.get("section_title"),
                    milvus_id=chunk_ids[i],
                )
                db.add(db_chunk)

            doc.status = DocumentStatus.indexed
            doc.chunk_count = len(chunks)
            await db.commit()

        except Exception as e:
            doc.status = DocumentStatus.failed
            doc.error_message = str(e)[:1000]
            await db.commit()
            raise


async def _get_collection_name(db, kb_id) -> str:
    from sqlalchemy import select
    from meks.models.knowledge_base import KnowledgeBase

    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one()
    return kb.milvus_collection
