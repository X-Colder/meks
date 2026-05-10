from fastapi import APIRouter

from meks.api.v1 import auth, documents, knowledge_bases, search, chat, users, system

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(documents.router, prefix="/documents", tags=["文档管理"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["知识库"])
api_router.include_router(search.router, prefix="/search", tags=["检索"])
api_router.include_router(chat.router, prefix="/chat", tags=["智能问答"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(system.router, prefix="/system", tags=["系统"])
