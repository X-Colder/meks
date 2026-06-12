from celery import Celery
import asyncio

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

celery_app.conf.beat_schedule = {
    "check-sync-schedule-every-minute": {
        "task": "meks.pipeline.tasks.check_sync_schedule",
        "schedule": 60.0,
    },
    "retry-stale-indexing-documents-every-ten-minutes": {
        "task": "meks.pipeline.tasks.retry_stale_indexing_documents",
        "schedule": 600.0,
    },
}


def run_async(coro):
    """在 Celery worker 中安全运行异步代码"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str):
    try:
        run_async(_process_document_async(document_id))
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        raise


async def _process_document_async(document_id: str):
    from uuid import UUID
    from sqlalchemy import select
    from meks.models.base import async_session, engine
    from meks.models.document import Document, DocumentStatus

    try:
        async with async_session() as db:
            result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
            doc = result.scalar_one_or_none()
            if not doc:
                return

            doc.status = DocumentStatus.processing
            doc.error_message = None
            await db.commit()

            try:
                await _reset_document_index(db, doc)

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

                analyze_paper_task.delay(str(doc.id), None)

                await _try_extract_medical_record(db, doc, text)

            except Exception as e:
                doc.status = DocumentStatus.failed
                doc.error_message = str(e)[:1000]
                await db.commit()
                raise
    finally:
        await engine.dispose()


async def _reset_document_index(db, doc) -> None:
    from sqlalchemy import delete
    from meks.models.chunk import DocumentChunk
    from meks.vectordb.operations import delete_by_document

    collection_name = await _get_collection_name(db, doc.knowledge_base_id)
    try:
        delete_by_document(collection_name, str(doc.id))
    except Exception:
        pass

    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    doc.chunk_count = 0
    await db.commit()


async def _try_extract_medical_record(db, doc, text: str):
    from meks.models.knowledge_base import KnowledgeBase, KBType
    from meks.models.document import ExtractionStatus
    from sqlalchemy import select

    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == doc.knowledge_base_id)
    )
    kb = result.scalar_one()
    if kb.kb_type != KBType.medical_record:
        return

    doc.extraction_status = ExtractionStatus.extracting
    await db.commit()

    try:
        from meks.llm.router import get_llm_provider
        from meks.services.extraction_service import extract_medical_record, save_medical_record

        provider = get_llm_provider()
        data = await extract_medical_record(text, provider)
        if data:
            await save_medical_record(db, doc.id, data)
        doc.extraction_status = ExtractionStatus.extracted
        await db.commit()
    except Exception:
        doc.extraction_status = ExtractionStatus.failed
        await db.commit()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def extract_medical_record_task(self, document_id: str):
    run_async(_extract_single_record(document_id))


async def _extract_single_record(document_id: str):
    from uuid import UUID
    from sqlalchemy import select
    from meks.models.base import async_session
    from meks.models.document import Document, ExtractionStatus
    from meks.pipeline.extractors import extract_text
    from meks.storage.client import download_file

    async with async_session() as db:
        result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
        doc = result.scalar_one_or_none()
        if not doc:
            return

        file_data = download_file(doc.storage_path)
        text, _ = extract_text(file_data, doc.file_type.value)
        await _try_extract_medical_record(db, doc, text)


async def _get_collection_name(db, kb_id) -> str:
    from sqlalchemy import select
    from meks.models.knowledge_base import KnowledgeBase

    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one()
    return kb.milvus_collection


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def run_sync_task(self, task_id: str):
    run_async(_run_sync_async(task_id))


async def _run_sync_async(task_id: str):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from meks.config import settings
    from meks.services.sync_service import execute_sync_task_with_session

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await execute_sync_task_with_session(task_id, session_factory)
    await engine.dispose()


@celery_app.task
def check_sync_schedule():
    run_async(_check_schedule())


async def _check_schedule():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from meks.config import settings
    from meks.models.sync_task import SyncTask, SyncStatus
    from sqlalchemy import select

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        result = await db.execute(
            select(SyncTask).where(
                SyncTask.status == SyncStatus.idle,
                SyncTask.cron_expr.isnot(None),
            )
        )
        tasks = result.scalars().all()
        now = datetime.now(ZoneInfo("Asia/Shanghai"))

        for task in tasks:
            if task.cron_expr and _should_run(task.cron_expr, task.last_sync_at, now):
                task.status = SyncStatus.running
                await db.commit()
                run_sync_task.delay(str(task.id))

    await engine.dispose()


def _should_run(cron_expr: str, last_run_at, now) -> bool:
    """支持常用 5 段 cron: minute hour day month weekday。"""
    from datetime import timezone

    fields = cron_expr.split()
    if len(fields) != 5:
        return False

    minute, hour, day, month, weekday = fields
    cron_weekday = (now.weekday() + 1) % 7
    values = [now.minute, now.hour, now.day, now.month, cron_weekday]
    if not all(
        _cron_field_matches(expr, value, minimum, maximum)
        for expr, value, minimum, maximum in [
            (minute, values[0], 0, 59),
            (hour, values[1], 0, 23),
            (day, values[2], 1, 31),
            (month, values[3], 1, 12),
            (weekday, values[4], 0, 6),
        ]
    ):
        return False

    current_slot_utc = now.astimezone(timezone.utc).replace(second=0, microsecond=0)
    if last_run_at is None:
        return True
    if last_run_at.tzinfo is None:
        last_run_at = last_run_at.replace(tzinfo=timezone.utc)
    return last_run_at < current_slot_utc


def _cron_field_matches(expr: str, value: int, minimum: int, maximum: int) -> bool:
    if expr == "*":
        return True
    for part in expr.split(","):
        step = 1
        if "/" in part:
            part, step_text = part.split("/", 1)
            try:
                step = int(step_text)
            except ValueError:
                return False
        if part == "*":
            start, end = minimum, maximum
        elif "-" in part:
            start_text, end_text = part.split("-", 1)
            try:
                start, end = int(start_text), int(end_text)
            except ValueError:
                return False
        else:
            try:
                start = end = int(part)
            except ValueError:
                return False
        if start <= value <= end and (value - start) % step == 0:
            return True
    return False


@celery_app.task
def retry_stale_indexing_documents():
    run_async(_retry_stale_indexing_documents())


async def _retry_stale_indexing_documents():
    from datetime import datetime, timedelta
    from sqlalchemy import or_, select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from meks.config import settings
    from meks.models.document import Document, DocumentStatus

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    cutoff = datetime.utcnow() - timedelta(minutes=30)
    async with session_factory() as db:
        result = await db.execute(
            select(Document)
            .where(
                or_(
                    Document.status == DocumentStatus.uploaded,
                    (
                        (Document.status == DocumentStatus.processing)
                        & (Document.updated_at < cutoff)
                    ),
                )
            )
            .order_by(Document.updated_at.asc())
            .limit(50)
        )
        docs = result.scalars().all()
        for doc in docs:
            process_document.delay(str(doc.id))

    await engine.dispose()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def analyze_paper_task(self, document_id: str, user_id: str | None = None):
    run_async(_analyze_paper_async(document_id, user_id))


async def _analyze_paper_async(document_id: str, user_id: str | None):
    from uuid import UUID
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from meks.config import settings
    from meks.models.paper_analysis import PaperAnalysis, AnalysisStatus
    from meks.services.paper_analysis_service import analyze_paper
    from sqlalchemy import select

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        try:
            await analyze_paper(
                UUID(document_id),
                db,
                UUID(user_id) if user_id else None,
            )
        except Exception as e:
            result = await db.execute(
                select(PaperAnalysis).where(PaperAnalysis.document_id == UUID(document_id))
            )
            analysis = result.scalar_one_or_none()
            if analysis:
                analysis.status = AnalysisStatus.failed
                analysis.error_message = str(e)[:1000]
                await db.commit()
    await engine.dispose()
