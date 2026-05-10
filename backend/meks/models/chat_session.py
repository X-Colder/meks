import enum
import uuid

from sqlalchemy import String, Text, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from meks.models.base import Base


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(256))
    knowledge_base_ids: Mapped[str] = mapped_column(Text)
    message_count: Mapped[int] = mapped_column(Integer, default=0)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    source_chunks: Mapped[str | None] = mapped_column(Text)
    llm_provider: Mapped[str | None] = mapped_column(String(32))
    model_name: Mapped[str | None] = mapped_column(String(64))
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
