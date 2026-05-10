from uuid import UUID

from pydantic import BaseModel


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    visibility: str = "department"
    department: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str | None
    visibility: str
    department: str | None
    document_count: int
    owner_id: str
    created_at: str

    model_config = {"from_attributes": True}
