from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    knowledge_base_ids: list[str] | None = None
    top_k: int = 10
    min_score: float = 0.5


class SearchResultItem(BaseModel):
    document_id: str
    document_title: str
    chunk_content: str
    score: float
    page_number: int | None
    section_title: str | None
    authors: str | None
    journal: str | None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    query: str
    total: int
    duration_ms: int
