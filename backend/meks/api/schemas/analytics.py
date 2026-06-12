from pydantic import BaseModel


class AnalyticsQueryRequest(BaseModel):
    query: str
    knowledge_base_ids: list[str] | None = None


class AnalyticsQueryResponse(BaseModel):
    intent_type: str
    columns: list[str]
    rows: list[dict]
    total: int
    query: str
    duration_ms: int
    semantic_results: list | None = None
