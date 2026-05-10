from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    authors: str | None
    journal: str | None
    doi: str | None
    publication_date: str | None
    abstract: str | None
    keywords: str | None
    chunk_count: int
    knowledge_base_id: str
    uploaded_by: str
    created_at: str
    error_message: str | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
