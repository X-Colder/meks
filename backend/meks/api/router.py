from fastapi import APIRouter

from meks.api.v1 import auth, documents, knowledge_bases, search, chat, users, system, analytics, audit_logs, sync_tasks, medical_records, paper_analysis, papers, frontier

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(documents.router, prefix="/documents", tags=["文档管理"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["知识库"])
api_router.include_router(search.router, prefix="/search", tags=["检索"])
api_router.include_router(chat.router, prefix="/chat", tags=["智能问答"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(system.router, prefix="/system", tags=["系统"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["统计分析"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["审计日志"])
api_router.include_router(sync_tasks.router, prefix="/sync-tasks", tags=["同步任务"])
api_router.include_router(medical_records.router, prefix="/medical-records", tags=["病历管理"])
api_router.include_router(paper_analysis.router, prefix="/paper-analysis", tags=["论文鉴真"])
api_router.include_router(papers.router, prefix="/papers", tags=["论文协作"])
api_router.include_router(frontier.router, prefix="/frontier", tags=["前沿发现"])
