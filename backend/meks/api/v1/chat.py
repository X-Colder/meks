import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from meks.api.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)
from meks.core.exceptions import NotFoundException
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.chat_session import ChatMessage, ChatSession, MessageRole
from meks.models.user import User

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    request: ChatSessionCreate,
    user: User = Depends(require_permission(Permission.CHAT_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    session = ChatSession(
        user_id=user.id,
        title=request.title or "新对话",
        knowledge_base_ids=json.dumps(request.knowledge_base_ids),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user: User = Depends(require_permission(Permission.CHAT_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    session_id: str,
    user: User = Depends(require_permission(Permission.CHAT_READ)),
    db: AsyncSession = Depends(get_db),
):
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    if not session_result.scalar_one_or_none():
        raise NotFoundException("对话")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == UUID(session_id))
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: ChatMessageRequest,
    user: User = Depends(require_permission(Permission.CHAT_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    chat_session = session_result.scalar_one_or_none()
    if not chat_session:
        raise NotFoundException("对话")

    user_msg = ChatMessage(
        session_id=UUID(session_id),
        role=MessageRole.user,
        content=request.content,
    )
    db.add(user_msg)
    await db.commit()

    # 提前读取 kb_ids，后面不再用 db
    kb_ids = json.loads(chat_session.knowledge_base_ids)

    from meks.services.chat_service import generate_rag_response
    from meks.models.base import async_session

    async def event_generator():
        full_response = ""
        source_chunks = []

        # SSE 生成器用独立 session
        async with async_session() as stream_db:
            async for chunk in generate_rag_response(
                query=request.content,
                knowledge_base_ids=kb_ids,
                db=stream_db,
            ):
                if chunk.get("type") == "sources":
                    source_chunks = chunk["data"]
                elif chunk.get("type") == "token":
                    full_response += chunk["data"]
                    yield {"event": "token", "data": chunk["data"]}
                elif chunk.get("type") == "done":
                    yield {"event": "done", "data": ""}

        # 保存助手消息用独立 session
        async with async_session() as save_db:
            assistant_msg = ChatMessage(
                session_id=UUID(session_id),
                role=MessageRole.assistant,
                content=full_response,
                source_chunks=json.dumps(source_chunks) if source_chunks else None,
            )
            save_db.add(assistant_msg)
            result = await save_db.execute(
                select(ChatSession).where(ChatSession.id == UUID(session_id))
            )
            session_to_update = result.scalar_one()
            session_to_update.message_count += 2
            await save_db.commit()

    return EventSourceResponse(event_generator())


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(require_permission(Permission.CHAT_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("对话")
    await db.delete(session)
    await db.commit()
    return {"detail": "对话已删除"}
