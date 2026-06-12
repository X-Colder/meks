import json
import logging
import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.models.document import Document, DocumentStatus, FileType
from meks.models.sync_task import SourceType, SyncStatus, SyncTask
from meks.pipeline.crawlers import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)


def _get_crawler(source_type: SourceType) -> BaseCrawler:
    if source_type == SourceType.pmc:
        from meks.pipeline.crawlers.pmc_crawler import PMCCrawler
        return PMCCrawler()
    elif source_type == SourceType.arxiv:
        from meks.pipeline.crawlers.arxiv_crawler import ArxivCrawler
        return ArxivCrawler()
    elif source_type == SourceType.biorxiv:
        from meks.pipeline.crawlers.biorxiv_crawler import BiorxivCrawler
        return BiorxivCrawler()
    elif source_type == SourceType.europepmc:
        from meks.pipeline.crawlers.europepmc_crawler import EuropePMCCrawler
        return EuropePMCCrawler()
    elif source_type == SourceType.semantic_scholar:
        from meks.pipeline.crawlers.semantic_scholar_crawler import SemanticScholarCrawler
        return SemanticScholarCrawler()
    else:
        raise ValueError(f"Unsupported source type: {source_type}")


async def create_sync_task(
    db: AsyncSession,
    name: str,
    source_type: str,
    config: dict,
    cron_expr: str | None,
    target_kb_id: str,
    user_id: str,
) -> SyncTask:
    task = SyncTask(
        name=name,
        source_type=SourceType(source_type),
        config=json.dumps(config),
        cron_expr=cron_expr,
        target_kb_id=uuid.UUID(target_kb_id),
        created_by=uuid.UUID(user_id),
        status=SyncStatus.idle,
        total_count=0,
        processed_count=0,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_sync_tasks(
    db: AsyncSession, kb_id: str | None = None
) -> list[SyncTask]:
    query = select(SyncTask)
    if kb_id:
        query = query.where(SyncTask.target_kb_id == uuid.UUID(kb_id))
    query = query.order_by(SyncTask.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_sync_task(db: AsyncSession, task_id: str) -> SyncTask | None:
    result = await db.execute(
        select(SyncTask).where(SyncTask.id == uuid.UUID(task_id))
    )
    return result.scalar_one_or_none()


async def execute_sync_task_with_session(task_id: str, session_factory) -> None:
    async with session_factory() as db:
        await _do_execute_sync(task_id, db)


async def execute_sync_task(task_id: str) -> None:
    from meks.models.base import async_session

    async with async_session() as db:
        await _do_execute_sync(task_id, db)


async def _do_execute_sync(task_id: str, db) -> None:
    task = await get_sync_task(db, task_id)
    if not task:
        logger.error("Sync task %s not found", task_id)
        return

    task.status = SyncStatus.running
    task.processed_count = 0
    await db.commit()

    try:
        crawler = _get_crawler(task.source_type)
        config = json.loads(task.config) if isinstance(task.config, str) else task.config

        query = config.get("query", "")
        max_results = int(config.get("max_results", 20))
        search_limit = int(config.get("search_limit", min(max_results * 3, 300)))
        watermark = _date_watermark(task.watermark)

        results = await crawler.search(
            query=query,
            max_results=search_limit,
            watermark=watermark,
        )
        results = _latest_first(_dedupe_results(results))

        task.total_count = max_results
        await db.commit()

        latest_seen_date = _parse_date(watermark) if watermark else None
        downloaded = 0

        for result in results:
            if downloaded >= max_results:
                break
            if result.published_date and (
                latest_seen_date is None or result.published_date > latest_seen_date
            ):
                latest_seen_date = result.published_date

            try:
                if await _document_exists(db, task.target_kb_id, result):
                    continue

                content = await crawler.download(result)

                from meks.storage.client import get_minio_client
                from meks.config import settings
                from io import BytesIO

                if content[:4] == b"%PDF":
                    file_ext = "pdf"
                    file_type = FileType.pdf
                else:
                    file_ext = "xml"
                    file_type = FileType.xml

                object_name = f"{task.target_kb_id}/{uuid.uuid4().hex}.{file_ext}"
                client = get_minio_client()
                client.put_object(
                    settings.minio_bucket,
                    object_name,
                    BytesIO(content),
                    length=len(content),
                    content_type="application/pdf" if file_type == FileType.pdf else "application/xml",
                )

                doc = Document(
                    title=result.title,
                    filename=f"{_safe_filename(result.external_id)}.{file_ext}",
                    file_type=file_type,
                    file_size_bytes=len(content),
                    storage_path=object_name,
                    status=DocumentStatus.uploaded,
                    authors=result.authors,
                    abstract=result.abstract,
                    doi=result.external_id,
                    publication_date=result.published_date,
                    journal=result.metadata.get("journal"),
                    knowledge_base_id=task.target_kb_id,
                    uploaded_by=task.created_by,
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)

                from meks.pipeline.tasks import process_document
                process_document.delay(str(doc.id))

                downloaded += 1

            except Exception:
                logger.warning(
                    "Failed to process crawl result %s",
                    result.external_id,
                    exc_info=True,
                )

            task.processed_count = downloaded
            await db.commit()

        if latest_seen_date:
            task.watermark = latest_seen_date.isoformat()
        task.status = SyncStatus.idle
        task.last_sync_at = datetime.utcnow()
        await db.commit()

        from meks.models.knowledge_base import KnowledgeBase
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count(Document.id)).where(Document.knowledge_base_id == task.target_kb_id)
        )
        doc_count = count_result.scalar() or 0
        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == task.target_kb_id)
        )
        kb = kb_result.scalar_one_or_none()
        if kb:
            kb.document_count = doc_count
            await db.commit()

    except Exception:
        logger.error("Sync task %s failed", task_id, exc_info=True)
        task.status = SyncStatus.failed
        await db.commit()


def _date_watermark(watermark: str | None) -> str | None:
    if not watermark:
        return None
    return watermark if _parse_date(watermark) else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _latest_first(results: list[CrawlResult]) -> list[CrawlResult]:
    return sorted(
        results,
        key=lambda r: (
            r.published_date or date.min,
            int(r.metadata.get("citation_count", 0) or 0),
        ),
        reverse=True,
    )


def _dedupe_results(results: list[CrawlResult]) -> list[CrawlResult]:
    seen: set[str] = set()
    deduped: list[CrawlResult] = []
    for result in results:
        key = result.external_id.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


async def _document_exists(db, kb_id, result: CrawlResult) -> bool:
    keys = {
        result.external_id,
        result.metadata.get("doi", ""),
        result.metadata.get("pmcid", ""),
        result.metadata.get("paper_id", ""),
    }
    normalized = [key.strip().lower() for key in keys if key and key.strip()]
    if not normalized:
        return False
    existing = await db.execute(
        select(Document.id).where(
            Document.knowledge_base_id == kb_id,
            func.lower(Document.doi).in_(normalized),
        )
    )
    return existing.scalar_one_or_none() is not None


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)[:180] or "paper"
