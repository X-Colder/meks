import json
import re
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.models.paper_analysis import PaperAnalysis, AnalysisStatus, RiskLevel
from meks.models.chunk import DocumentChunk
from meks.models.document import Document
from meks.llm.prompts.paper_analysis import PAPER_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

MAX_TEXT_LEN = 12000
REQUIRED_ANALYSIS_KEYS = {
    "data_statistics",
    "logic_consistency",
    "credibility_signals",
    "reproducibility",
    "figure_consistency",
    "citation_manipulation",
    "overall",
}


class AnalysisParseError(ValueError):
    pass


def _parse_analysis_response(raw: str) -> dict:
    raw = raw.strip()
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _has_required_analysis_keys(data: dict) -> bool:
    return REQUIRED_ANALYSIS_KEYS.issubset(data.keys())


async def _completion_with_json_retry(provider, prompt: str) -> tuple[str, dict]:
    raw_response = await provider.completion(prompt)
    data = _parse_analysis_response(raw_response)
    if _has_required_analysis_keys(data):
        return raw_response, data

    retry_prompt = (
        prompt
        + "\n\n上一次输出不是可解析的完整 JSON。请重新输出严格合法 JSON："
        + "不要使用 Markdown，不要省略字段，字符串内不要换行，不要包含 JSON 之外的任何文字。"
    )
    raw_retry = await provider.completion(retry_prompt)
    retry_data = _parse_analysis_response(raw_retry)
    if _has_required_analysis_keys(retry_data):
        return raw_retry, retry_data

    preview = (raw_retry or raw_response).replace("\n", " ")[:500]
    raise AnalysisParseError(f"模型返回不是可解析的论文鉴真 JSON：{preview}")


def _clamp_score(val) -> int | None:
    if val is None:
        return None
    try:
        return max(0, min(100, int(val)))
    except (ValueError, TypeError):
        return None


def _parse_risk_level(val: str | None) -> RiskLevel | None:
    if not val:
        return None
    try:
        return RiskLevel(val.lower())
    except ValueError:
        return None


def _json_list_to_str(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, str):
        return val
    return None


async def analyze_paper(document_id: UUID, db: AsyncSession, user_id: UUID | None = None) -> PaperAnalysis:
    result = await db.execute(
        select(PaperAnalysis).where(PaperAnalysis.document_id == document_id)
    )
    analysis = result.scalar_one_or_none()

    if analysis is None:
        analysis = PaperAnalysis(document_id=document_id, analyzed_by=user_id)
        db.add(analysis)
    else:
        analysis.analyzed_by = user_id

    analysis.status = AnalysisStatus.analyzing
    analysis.error_message = None
    await db.commit()
    await db.refresh(analysis)

    try:
        chunks_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = chunks_result.scalars().all()

        if chunks:
            text = " ".join(c.content for c in chunks)[:MAX_TEXT_LEN]
        else:
            doc_result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = doc_result.scalar_one_or_none()
            text = (doc.abstract or "") if doc else ""

        from meks.llm.router import get_llm_provider
        provider = get_llm_provider()
        prompt = PAPER_ANALYSIS_PROMPT.format(text=text)
        raw_response, data = await _completion_with_json_retry(provider, prompt)

        ds = data.get("data_statistics", {})
        lc = data.get("logic_consistency", {})
        cs = data.get("credibility_signals", {})
        rp = data.get("reproducibility", {})
        fc = data.get("figure_consistency", {})
        cm = data.get("citation_manipulation", {})
        ov = data.get("overall", {})

        analysis.data_statistics_score = _clamp_score(ds.get("score"))
        analysis.data_statistics_verdict = ds.get("verdict")
        analysis.logic_consistency_score = _clamp_score(lc.get("score"))
        analysis.logic_consistency_verdict = lc.get("verdict")
        analysis.credibility_score = _clamp_score(cs.get("score"))
        analysis.credibility_verdict = cs.get("verdict")
        analysis.reproducibility_score = _clamp_score(rp.get("score"))
        analysis.reproducibility_verdict = rp.get("verdict")
        analysis.figure_consistency_score = _clamp_score(fc.get("score"))
        analysis.figure_consistency_verdict = fc.get("verdict")
        analysis.citation_manipulation_score = _clamp_score(cm.get("score"))
        analysis.citation_manipulation_verdict = cm.get("verdict")
        analysis.overall_risk_score = _clamp_score(ov.get("risk_score"))
        analysis.risk_level = _parse_risk_level(ov.get("risk_level"))

        ds_items = (ds.get("findings") or []) + (ds.get("red_flags") or [])
        lc_items = (lc.get("findings") or []) + (lc.get("red_flags") or [])
        cs_items = (cs.get("findings") or []) + (cs.get("red_flags") or [])
        rp_items = (rp.get("findings") or []) + (rp.get("red_flags") or [])
        fc_items = (fc.get("findings") or []) + (fc.get("red_flags") or [])
        cm_items = (cm.get("findings") or []) + (cm.get("red_flags") or [])

        analysis.data_statistics_findings = _json_list_to_str(ds_items) if ds_items else None
        analysis.logic_consistency_findings = _json_list_to_str(lc_items) if lc_items else None
        analysis.credibility_findings = _json_list_to_str(cs_items) if cs_items else None
        analysis.reproducibility_findings = _json_list_to_str(rp_items) if rp_items else None
        analysis.figure_consistency_findings = _json_list_to_str(fc_items) if fc_items else None
        analysis.citation_manipulation_findings = _json_list_to_str(cm_items) if cm_items else None
        analysis.overall_summary = ov.get("summary")
        analysis.recommendations = _json_list_to_str(ov.get("recommendations"))

        analysis.status = AnalysisStatus.completed

    except Exception as e:
        logger.exception("Paper analysis failed for document %s", document_id)
        analysis.status = AnalysisStatus.failed
        analysis.error_message = str(e)[:1000]

    await db.commit()
    await db.refresh(analysis)
    return analysis
