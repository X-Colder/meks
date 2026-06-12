import json
import logging
import re
import time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.llm.base import LLMProvider
from meks.llm.prompts.extraction import QUERY_INTENT_PROMPT
from meks.models.document import Document
from meks.models.medical_record import MedicalRecord, Severity, TreatmentOutcome

logger = logging.getLogger(__name__)

# Hardcoded whitelist of columns allowed in structured queries.
# Column names MUST be validated against this set before use.
ALLOWED_COLUMNS: dict[str, object] = {
    "patient_name": MedicalRecord.patient_name,
    "gender": MedicalRecord.gender,
    "age": MedicalRecord.age,
    "phone": MedicalRecord.phone,
    "occupation": MedicalRecord.occupation,
    "admission_date": MedicalRecord.admission_date,
    "discharge_date": MedicalRecord.discharge_date,
    "hospital_days": MedicalRecord.hospital_days,
    "department": MedicalRecord.department,
    "attending_doctor": MedicalRecord.attending_doctor,
    "primary_diagnosis": MedicalRecord.primary_diagnosis,
    "icd10_code": MedicalRecord.icd10_code,
    "severity": MedicalRecord.severity,
    "treatment_type": MedicalRecord.treatment_type,
    "treatment_outcome": MedicalRecord.treatment_outcome,
}

ALLOWED_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "contains", "in"}
ALLOWED_AGGREGATIONS = {"count", "avg", "sum", "min", "max", "group_by"}


def _parse_intent_response(raw: str) -> dict:
    """Parse the LLM JSON response, extracting the first JSON object found."""
    raw = raw.strip()
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _validate_column(column_name: str):
    """Validate that a column name is in the whitelist. Raises ValueError if not."""
    if column_name not in ALLOWED_COLUMNS:
        raise ValueError(f"Column '{column_name}' is not allowed for queries")


def _coerce_value(column_name: str, value):
    """Coerce a filter value to the appropriate Python type for the column."""
    if value is None:
        return None
    # Enum columns
    if column_name == "severity":
        return Severity(str(value).lower())
    if column_name == "treatment_outcome":
        return TreatmentOutcome(str(value).lower())
    # Integer columns
    if column_name in ("age", "hospital_days"):
        return int(value)
    return str(value)


def _apply_filter(query, column_name: str, operator: str, value):
    """Apply a single filter to a SQLAlchemy query using parameterized operations."""
    _validate_column(column_name)

    if operator not in ALLOWED_OPERATORS:
        raise ValueError(f"Operator '{operator}' is not allowed")

    col = ALLOWED_COLUMNS[column_name]

    if operator == "in":
        if not isinstance(value, list):
            value = [value]
        coerced = [_coerce_value(column_name, v) for v in value]
        return query.where(col.in_(coerced))

    coerced = _coerce_value(column_name, value)

    if operator == "eq":
        return query.where(col == coerced)
    elif operator == "ne":
        return query.where(col != coerced)
    elif operator == "gt":
        return query.where(col > coerced)
    elif operator == "gte":
        return query.where(col >= coerced)
    elif operator == "lt":
        return query.where(col < coerced)
    elif operator == "lte":
        return query.where(col <= coerced)
    elif operator == "contains":
        return query.where(col.contains(str(coerced)))

    raise ValueError(f"Unsupported operator: {operator}")


async def analyze_query_intent(query: str, provider: LLMProvider) -> dict:
    """Use LLM to classify a natural-language query into a structured intent."""
    prompt = QUERY_INTENT_PROMPT.format(query=query)
    raw_response = await provider.completion(prompt)
    intent = _parse_intent_response(raw_response)

    # Ensure required fields have defaults
    intent.setdefault("intent_type", "semantic")
    intent.setdefault("filters", [])
    intent.setdefault("aggregation", None)
    intent.setdefault("group_by", None)
    intent.setdefault("semantic_query", None)

    return intent


async def execute_structured_query(
    intent: dict,
    db: AsyncSession,
    kb_ids: list[str] | None = None,
) -> dict:
    """Build and execute a safe, parameterized SQLAlchemy query against medical_records."""
    filters = intent.get("filters", [])
    aggregation = intent.get("aggregation")
    group_by_col = intent.get("group_by")

    # Validate group_by column early
    if group_by_col:
        _validate_column(group_by_col)

    # Validate aggregation
    if aggregation and aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"Aggregation '{aggregation}' is not allowed")

    # Determine what to SELECT
    if aggregation == "count" and group_by_col:
        group_col = ALLOWED_COLUMNS[group_by_col]
        stmt = select(group_col.label("group_key"), func.count().label("count"))
    elif aggregation == "count":
        stmt = select(func.count().label("count"))
    elif aggregation in ("avg", "sum", "min", "max") and group_by_col:
        # Aggregation with group_by requires a numeric target column from filters
        agg_col_name = _infer_agg_column(filters, aggregation)
        _validate_column(agg_col_name)
        agg_col = ALLOWED_COLUMNS[agg_col_name]
        group_col = ALLOWED_COLUMNS[group_by_col]
        agg_func = {"avg": func.avg, "sum": func.sum, "min": func.min, "max": func.max}[aggregation]
        stmt = select(group_col.label("group_key"), agg_func(agg_col).label(aggregation))
    elif aggregation in ("avg", "sum", "min", "max"):
        agg_col_name = _infer_agg_column(filters, aggregation)
        _validate_column(agg_col_name)
        agg_col = ALLOWED_COLUMNS[agg_col_name]
        agg_func = {"avg": func.avg, "sum": func.sum, "min": func.min, "max": func.max}[aggregation]
        stmt = select(agg_func(agg_col).label(aggregation))
    else:
        # Return matching rows with all whitelisted columns
        stmt = select(MedicalRecord)

    # Join with documents for knowledge_base filtering
    if kb_ids:
        stmt = stmt.join(Document, MedicalRecord.document_id == Document.id)
        stmt = stmt.where(Document.knowledge_base_id.in_([UUID(kid) for kid in kb_ids]))

    # Apply filters
    for f in filters:
        col_name = f.get("column", "")
        operator = f.get("operator", "eq")
        value = f.get("value")
        try:
            stmt = _apply_filter(stmt, col_name, operator, value)
        except (ValueError, KeyError) as e:
            logger.warning("Skipping invalid filter %s: %s", f, e)
            continue

    # Apply group_by
    if group_by_col and aggregation:
        group_col = ALLOWED_COLUMNS[group_by_col]
        stmt = stmt.group_by(group_col)

    result = await db.execute(stmt)

    # Format output
    if aggregation and group_by_col:
        rows_raw = result.all()
        columns = ["group_key", aggregation]
        rows = [{"group_key": str(r[0]) if r[0] is not None else None, aggregation: r[1]} for r in rows_raw]
    elif aggregation:
        scalar = result.scalar()
        columns = [aggregation]
        rows = [{aggregation: scalar}]
    else:
        records = result.scalars().all()
        columns = list(ALLOWED_COLUMNS.keys())
        rows = []
        for rec in records:
            row = {}
            for col_name in columns:
                val = getattr(rec, col_name, None)
                # Convert enums and dates to strings for JSON serialization
                if val is not None and hasattr(val, "value"):
                    val = val.value
                elif val is not None and hasattr(val, "isoformat"):
                    val = val.isoformat()
                row[col_name] = val
            rows.append(row)

    return {
        "columns": columns,
        "rows": rows,
        "total": len(rows),
    }


def _infer_agg_column(filters: list[dict], aggregation: str) -> str:
    """Infer which numeric column to aggregate based on context.

    Defaults to common numeric columns when the filters don't make it obvious.
    """
    numeric_columns = {"age", "hospital_days"}
    # Check if any filter references a numeric column
    for f in filters:
        if f.get("column") in numeric_columns:
            return f["column"]
    # Default to age for avg/sum/min/max
    return "age"


async def execute_hybrid_query(
    intent: dict,
    db: AsyncSession,
    kb_ids: list[str] | None = None,
) -> dict:
    """Execute a hybrid query: SQL filter to get document IDs, then semantic search."""
    # Step 1: Run structured filters to get matching document IDs
    filters = intent.get("filters", [])

    doc_id_stmt = select(MedicalRecord.document_id)

    if kb_ids:
        doc_id_stmt = doc_id_stmt.join(
            Document, MedicalRecord.document_id == Document.id
        )
        doc_id_stmt = doc_id_stmt.where(
            Document.knowledge_base_id.in_([UUID(kid) for kid in kb_ids])
        )

    for f in filters:
        col_name = f.get("column", "")
        operator = f.get("operator", "eq")
        value = f.get("value")
        try:
            doc_id_stmt = _apply_filter(doc_id_stmt, col_name, operator, value)
        except (ValueError, KeyError) as e:
            logger.warning("Skipping invalid filter %s: %s", f, e)
            continue

    result = await db.execute(doc_id_stmt)
    doc_ids = [str(row[0]) for row in result.all()]

    if not doc_ids:
        return {
            "columns": [],
            "rows": [],
            "total": 0,
            "semantic_results": [],
        }

    # Step 2: Build Milvus filter expression from document IDs
    # Use quoted IDs in a Milvus 'in' expression
    escaped_ids = [did.replace('"', '\\"') for did in doc_ids]
    id_list = ", ".join(f'"{did}"' for did in escaped_ids)
    milvus_expr = f"document_id in [{id_list}]"

    # Step 3: Run semantic search with Milvus expression filter
    semantic_query = intent.get("semantic_query") or ""

    from meks.services.search_service import execute_semantic_search
    from meks.vectordb.operations import search_vectors
    from meks.pipeline.embedders.local_embedder import generate_embeddings
    from meks.models.knowledge_base import KnowledgeBase

    query_embedding = generate_embeddings([semantic_query])[0]

    semantic_results = []

    if not kb_ids:
        kb_result = await db.execute(select(KnowledgeBase))
        kbs = kb_result.scalars().all()
    else:
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id.in_([UUID(kid) for kid in kb_ids])
            )
        )
        kbs = kb_result.scalars().all()

    for kb in kbs:
        try:
            hits = search_vectors(
                collection_name=kb.milvus_collection,
                query_embedding=query_embedding,
                top_k=10,
                expr=milvus_expr,
            )
            for hit in hits:
                if hit["score"] >= 0.3:
                    semantic_results.append({**hit, "knowledge_base_id": str(kb.id)})
        except Exception:
            continue

    semantic_results.sort(key=lambda x: x["score"], reverse=True)
    semantic_results = semantic_results[:10]

    # Enrich semantic results with document titles
    enriched = []
    for r in semantic_results:
        doc_result = await db.execute(
            select(Document).where(Document.id == UUID(r["document_id"]))
        )
        doc = doc_result.scalar_one_or_none()
        enriched.append({
            "document_id": r["document_id"],
            "document_title": doc.title if doc else "Unknown",
            "chunk_content": r["content"],
            "score": r["score"],
        })

    return {
        "columns": ["document_id", "document_title", "chunk_content", "score"],
        "rows": enriched,
        "total": len(enriched),
        "semantic_results": enriched,
    }


async def execute_analytics_query(
    query: str,
    db: AsyncSession,
    kb_ids: list[str] | None = None,
) -> dict:
    """Orchestrator: analyze intent, route to correct execution path, measure duration."""
    start_time = time.time()

    from meks.llm.router import get_llm_provider

    provider = get_llm_provider()

    # Step 1: Analyze query intent
    intent = await analyze_query_intent(query, provider)
    intent_type = intent.get("intent_type", "semantic")

    # Step 2: Route to the correct execution path
    if intent_type == "structured":
        result = await execute_structured_query(intent, db, kb_ids)
    elif intent_type == "hybrid":
        result = await execute_hybrid_query(intent, db, kb_ids)
    elif intent_type == "semantic":
        from meks.services.search_service import execute_semantic_search

        semantic_results = await execute_semantic_search(
            query=intent.get("semantic_query") or query,
            knowledge_base_ids=kb_ids,
            top_k=10,
            min_score=0.3,
            db=db,
        )
        result = {
            "columns": ["document_id", "document_title", "chunk_content", "score"],
            "rows": [
                {
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "chunk_content": r.chunk_content,
                    "score": r.score,
                }
                for r in semantic_results
            ],
            "total": len(semantic_results),
            "semantic_results": [
                {
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "chunk_content": r.chunk_content,
                    "score": r.score,
                }
                for r in semantic_results
            ],
        }
    else:
        # Fallback to structured
        result = await execute_structured_query(intent, db, kb_ids)

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "intent_type": intent_type,
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "total": result.get("total", 0),
        "query": query,
        "duration_ms": duration_ms,
        "semantic_results": result.get("semantic_results"),
    }
