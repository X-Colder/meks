from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    title: str | None = None
    knowledge_base_ids: list[str]


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    knowledge_base_ids: str
    message_count: int
    created_at: str

    model_config = {"from_attributes": True}


class ChatMessageRequest(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    source_chunks: str | None
    llm_provider: str | None
    model_name: str | None
    created_at: str

    model_config = {"from_attributes": True}
