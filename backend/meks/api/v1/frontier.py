import json
import math
import re
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.frontier import (
    FocusPointCreate,
    FocusPointResponse,
    FrontierPaper,
    FrontierResponse,
    FrontierTopic,
    FrontierTrend,
)
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.document import Document, DocumentStatus
from meks.models.focus_point import FocusPoint
from meks.models.knowledge_base import KnowledgeBase
from meks.models.paper_analysis import PaperAnalysis
from meks.models.sync_task import SyncTask
from meks.models.user import User

router = APIRouter()

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "using", "study",
    "research", "analysis", "cardiovascular", "disease", "diseases", "patient",
    "patients", "clinical", "based", "effect", "effects", "risk", "among",
}


def _parse_config(config: str | dict | None) -> dict:
    if isinstance(config, dict):
        return config
    if not config:
        return {}
    try:
        return json.loads(config)
    except json.JSONDecodeError:
        return {}


async def _focus_response(db: AsyncSession, focus: FocusPoint) -> FocusPointResponse:
    kb_name = None
    sync_status = None
    if focus.knowledge_base_id:
        kb = await db.get(KnowledgeBase, focus.knowledge_base_id)
        kb_name = kb.name if kb else None
    if focus.sync_task_id:
        task = await db.get(SyncTask, focus.sync_task_id)
        sync_status = task.status.value if task else None
    return FocusPointResponse(
        id=str(focus.id),
        name=focus.name,
        query=focus.query,
        source_type=focus.source_type,
        max_results=focus.max_results,
        cron_expr=focus.cron_expr,
        knowledge_base_id=str(focus.knowledge_base_id) if focus.knowledge_base_id else None,
        knowledge_base_name=kb_name,
        sync_task_id=str(focus.sync_task_id) if focus.sync_task_id else None,
        sync_status=sync_status,
        last_message=focus.last_message,
        created_at=focus.created_at,
    )


async def _create_kb_for_focus(db: AsyncSession, user: User, request: FocusPointCreate) -> KnowledgeBase:
    from meks.models.knowledge_base import KBType, Visibility
    from meks.vectordb.collections import create_collection

    collection_name = f"meks_kb_{uuid.uuid4().hex[:12]}"
    create_collection(collection_name)
    kb = KnowledgeBase(
        name=request.name,
        description=f"由前沿关注点创建：{request.query}",
        owner_id=user.id,
        visibility=Visibility.department,
        department=user.department,
        milvus_collection=collection_name,
        kb_type=KBType.literature,
    )
    db.add(kb)
    await db.flush()
    return kb

async def _create_sync_for_focus(db: AsyncSession, user: User, focus: FocusPoint) -> SyncTask:
    from meks.models.sync_task import SourceType, SyncStatus

    task = SyncTask(
        name=focus.name,
        source_type=SourceType(focus.source_type),
        config=json.dumps({"query": focus.query, "max_results": focus.max_results}),
        cron_expr=focus.cron_expr,
        target_kb_id=focus.knowledge_base_id,
        created_by=user.id,
        status=SyncStatus.running,
        total_count=0,
        processed_count=0,
    )
    db.add(task)
    await db.flush()
    focus.sync_task_id = task.id
    focus.last_message = "已创建同步任务，正在下载论文"
    return task


def _score_document(doc: Document) -> tuple[int, list[str], str]:
    score = 35
    reasons: list[str] = []
    today = date.today()

    if doc.publication_date:
        age_days = max(0, (today - doc.publication_date).days)
        recency = max(0, 40 - int(age_days / 7))
        score += recency
        if age_days <= 30:
            reasons.append("近 30 天发表")
        elif age_days <= 90:
            reasons.append("近 90 天发表")
    else:
        age_hours = max(0, (datetime.utcnow() - doc.created_at).total_seconds() / 3600)
        score += max(0, 20 - int(age_hours / 24))
        reasons.append("新近导入")

    title_abstract = f"{doc.title} {doc.abstract or ''}".lower()
    if any(term in title_abstract for term in ("meta-analysis", "systematic review", "randomized", "trial", "guideline")):
        score += 12
        reasons.append("证据类型较高")
    if any(term in title_abstract for term in ("machine learning", "deep learning", "omics", "biomarker", "single-cell", "multi-omics")):
        score += 10
        reasons.append("包含前沿方法或标志物")
    if doc.status == DocumentStatus.indexed:
        score += 8
        reasons.append("已完成索引")
    else:
        reasons.append("已导入，待索引")

    score = max(0, min(100, score))
    if score >= 75:
        recommendation = "重点精读"
    elif score >= 55:
        recommendation = "建议浏览"
    else:
        recommendation = "可作为背景材料"
    return score, reasons[:4], recommendation


def _trend_keywords(docs: list[Document]) -> list[FrontierTrend]:
    counter: Counter[str] = Counter()
    for doc in docs:
        text = f"{doc.title} {doc.abstract or ''}".lower()
        for word in re.findall(r"[a-z][a-z-]{3,}", text):
            if word not in STOPWORDS:
                counter[word] += 1
    return [FrontierTrend(keyword=word, count=count) for word, count in counter.most_common(12)]


def _relevance_score(doc: Document, query: str | None) -> int:
    if not query:
        return 0
    terms = [
        term
        for term in re.split(r"\s+|\bor\b|\band\b", query.lower().replace("(", " ").replace(")", " ").replace('"', " "))
        if len(term.strip()) > 2
    ]
    if not terms:
        return 0
    text = f"{doc.title} {doc.abstract or ''} {doc.authors or ''} {doc.journal or ''}".lower()
    hits = sum(1 for term in terms if term.strip() in text)
    return max(0, min(100, round((hits / len(terms)) * 100)))


@router.get("/focus-points", response_model=list[FocusPointResponse])
async def list_focus_points(
    user: User = Depends(require_permission(Permission.SYNC_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FocusPoint)
        .where(FocusPoint.owner_id == user.id)
        .order_by(FocusPoint.created_at.desc())
    )
    return [await _focus_response(db, focus) for focus in result.scalars().all()]


@router.post("/focus-points", response_model=FocusPointResponse)
async def create_focus_point(
    request: FocusPointCreate,
    user: User = Depends(require_permission(Permission.SYNC_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    kb = None
    if request.knowledge_base_id:
        kb = await db.get(KnowledgeBase, UUID(request.knowledge_base_id))
    else:
        kb = await _create_kb_for_focus(db, user, request)

    focus = FocusPoint(
        name=request.name,
        query=request.query,
        source_type=request.source_type,
        max_results=request.max_results,
        cron_expr=request.cron_expr,
        knowledge_base_id=kb.id if kb else None,
        owner_id=user.id,
        last_message="关注点已创建",
    )
    db.add(focus)
    await db.flush()

    task = None
    if request.auto_sync and focus.knowledge_base_id:
        task = await _create_sync_for_focus(db, user, focus)

    await db.commit()
    await db.refresh(focus)

    if task:
        from meks.pipeline.tasks import run_sync_task
        run_sync_task.delay(str(task.id))

    return await _focus_response(db, focus)


@router.delete("/focus-points/{focus_id}")
async def delete_focus_point(
    focus_id: str,
    user: User = Depends(require_permission(Permission.SYNC_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FocusPoint).where(FocusPoint.id == UUID(focus_id), FocusPoint.owner_id == user.id)
    )
    focus = result.scalar_one_or_none()
    if focus:
        await db.delete(focus)
        await db.commit()
    return {"detail": "关注点已删除"}


@router.get("", response_model=FrontierResponse)
async def list_frontier(
    topic_id: str | None = Query(None),
    kb_id: str | None = Query(None),
    days: int = Query(90, ge=1, le=3650),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    topics_result = await db.execute(
        select(SyncTask, KnowledgeBase)
        .join(KnowledgeBase, KnowledgeBase.id == SyncTask.target_kb_id)
        .order_by(SyncTask.created_at.desc())
    )
    task_rows = topics_result.all()

    doc_counts = await db.execute(
        select(Document.knowledge_base_id, Document.status, func.count(Document.id))
        .group_by(Document.knowledge_base_id, Document.status)
    )
    count_map: dict[str, dict[str, int]] = {}
    for kb_uuid, doc_status, count in doc_counts.all():
        item = count_map.setdefault(str(kb_uuid), {})
        item[doc_status.value] = count

    topics: list[FrontierTopic] = []
    task_by_kb: dict[str, SyncTask] = {}
    for task, kb in task_rows:
        config = _parse_config(task.config)
        kb_key = str(kb.id)
        task_by_kb.setdefault(kb_key, task)
        counts = count_map.get(kb_key, {})
        topics.append(
            FrontierTopic(
                id=str(task.id),
                name=task.name,
                source_type=task.source_type.value,
                query=config.get("query", ""),
                knowledge_base_id=kb_key,
                knowledge_base_name=kb.name,
                cadence=task.cron_expr,
                last_sync_at=task.last_sync_at,
                document_count=sum(counts.values()),
                indexed_count=counts.get(DocumentStatus.indexed.value, 0),
            )
        )

    query = select(Document, KnowledgeBase).join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
    if topic_id:
        task_result = await db.execute(select(SyncTask).where(SyncTask.id == UUID(topic_id)))
        task = task_result.scalar_one_or_none()
        if task:
            query = query.where(Document.knowledge_base_id == task.target_kb_id)
    if kb_id:
        query = query.where(Document.knowledge_base_id == UUID(kb_id))
    if status:
        query = query.where(Document.status == DocumentStatus(status))

    cutoff_date = date.today() - timedelta(days=days)
    cutoff_datetime = datetime.utcnow() - timedelta(days=days)
    query = query.where(
        or_(
            Document.publication_date >= cutoff_date,
            Document.created_at >= cutoff_datetime,
        )
    )
    query = query.order_by(Document.publication_date.desc().nullslast(), Document.created_at.desc()).limit(limit * 3)

    doc_rows = (await db.execute(query)).all()
    analysis_result = await db.execute(select(PaperAnalysis))
    analysis_by_doc = {str(item.document_id): item for item in analysis_result.scalars().all()}
    relevance_query = None
    if topic_id:
        task_result = await db.execute(select(SyncTask).where(SyncTask.id == UUID(topic_id)))
        task = task_result.scalar_one_or_none()
        if task:
            relevance_query = _parse_config(task.config).get("query")
    elif kb_id:
        task = task_by_kb.get(kb_id)
        relevance_query = _parse_config(task.config).get("query") if task else None
    scored: list[tuple[int, FrontierPaper, Document]] = []
    for doc, kb in doc_rows:
        score, reasons, recommendation = _score_document(doc)
        source_task = task_by_kb.get(str(kb.id))
        analysis = analysis_by_doc.get(str(doc.id))
        rel_score = _relevance_score(doc, relevance_query or (_parse_config(source_task.config).get("query") if source_task else None))
        scored.append(
            (
                score,
                FrontierPaper(
                    document_id=str(doc.id),
                    title=doc.title,
                    authors=doc.authors,
                    journal=doc.journal,
                    doi=doc.doi,
                    abstract=doc.abstract,
                    publication_date=doc.publication_date,
                    created_at=doc.created_at,
                    status=doc.status.value,
                    knowledge_base_id=str(kb.id),
                    knowledge_base_name=kb.name,
                    source_type=source_task.source_type.value if source_task else None,
                    frontier_score=score,
                    relevance_score=rel_score,
                    analysis_risk_score=analysis.overall_risk_score if analysis else None,
                    risk_level=analysis.risk_level.value if analysis and analysis.risk_level else None,
                    reasons=reasons,
                    recommendation=recommendation,
                ),
                doc,
            )
        )

    scored.sort(key=lambda item: (item[0], item[1].publication_date or date.min, item[1].created_at), reverse=True)
    papers = [item[1] for item in scored[:limit]]
    trend_docs = [item[2] for item in scored[:limit]]

    return FrontierResponse(
        topics=topics,
        papers=papers,
        trends=_trend_keywords(trend_docs),
        total=len(papers),
    )
