from datetime import date, datetime

from pydantic import BaseModel


class FrontierTopic(BaseModel):
    id: str
    name: str
    source_type: str
    query: str
    knowledge_base_id: str
    knowledge_base_name: str
    cadence: str | None = None
    last_sync_at: datetime | None = None
    document_count: int
    indexed_count: int


class FocusPointCreate(BaseModel):
    name: str
    query: str
    source_type: str = "pmc"
    max_results: int = 50
    cron_expr: str | None = None
    knowledge_base_id: str | None = None
    auto_sync: bool = True


class FocusPointResponse(BaseModel):
    id: str
    name: str
    query: str
    source_type: str
    max_results: int
    cron_expr: str | None
    knowledge_base_id: str | None
    knowledge_base_name: str | None
    sync_task_id: str | None
    sync_status: str | None
    last_message: str | None
    created_at: datetime


class FrontierPaper(BaseModel):
    document_id: str
    title: str
    authors: str | None
    journal: str | None
    doi: str | None
    abstract: str | None
    publication_date: date | None
    created_at: datetime
    status: str
    knowledge_base_id: str
    knowledge_base_name: str
    source_type: str | None
    frontier_score: int
    relevance_score: int
    analysis_risk_score: int | None = None
    risk_level: str | None = None
    reasons: list[str]
    recommendation: str


class FrontierTrend(BaseModel):
    keyword: str
    count: int


class FrontierResponse(BaseModel):
    topics: list[FrontierTopic]
    papers: list[FrontierPaper]
    trends: list[FrontierTrend]
    total: int
