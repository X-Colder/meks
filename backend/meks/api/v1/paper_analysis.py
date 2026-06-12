from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.paper_analysis import PaperAnalysisResponse
from meks.core.exceptions import NotFoundException
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.paper_analysis import PaperAnalysis, AnalysisStatus
from meks.models.user import User

router = APIRouter()


@router.post("/{document_id}", status_code=202)
async def trigger_paper_analysis(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PaperAnalysis).where(PaperAnalysis.document_id == UUID(document_id))
    )
    analysis = result.scalar_one_or_none()

    if analysis is None:
        analysis = PaperAnalysis(
            document_id=UUID(document_id),
            status=AnalysisStatus.pending,
            analyzed_by=user.id,
        )
        db.add(analysis)
        await db.commit()

    from meks.pipeline.tasks import analyze_paper_task
    analyze_paper_task.delay(document_id, str(user.id))

    return {"detail": "论文鉴真任务已提交", "document_id": document_id}


@router.get("/{document_id}", response_model=PaperAnalysisResponse)
async def get_paper_analysis(
    document_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PaperAnalysis).where(PaperAnalysis.document_id == UUID(document_id))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise NotFoundException("论文鉴真记录")
    return analysis
