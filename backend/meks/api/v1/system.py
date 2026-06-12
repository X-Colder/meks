import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.system import LLMSettingsResponse, LLMSettingsUpdate
from meks.config import settings
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.llm.router import _is_vllm_available, get_llm_provider
from meks.models.base import get_db
from meks.models.document import Document, DocumentStatus
from meks.models.knowledge_base import KnowledgeBase
from meks.models.user import User

router = APIRouter()


@router.get("/stats")
async def system_stats(
    user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
    db: AsyncSession = Depends(get_db),
):
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    kb_count = (await db.execute(select(func.count(KnowledgeBase.id)))).scalar() or 0
    indexed_count = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == DocumentStatus.indexed)
        )
    ).scalar() or 0

    return {
        "users": user_count,
        "documents": doc_count,
        "knowledge_bases": kb_count,
        "indexed_documents": indexed_count,
    }


@router.get("/health")
async def detailed_health():
    checks = {}

    try:
        from meks.models.base import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    try:
        from meks.vectordb.client import get_milvus_client
        client = get_milvus_client()
        checks["milvus"] = "ok" if client else "not initialized"
    except Exception as e:
        checks["milvus"] = f"error: {e}"

    import httpx
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{settings.vllm_embed_url}/health")
            checks["vllm_embed"] = "ok" if r.status_code == 200 else f"status {r.status_code}"
        except Exception as e:
            checks["vllm_embed"] = f"error: {e}"

        try:
            r = await client.get(f"{settings.vllm_chat_url}/health")
            checks["vllm_chat"] = "ok" if r.status_code == 200 else f"status {r.status_code}"
        except Exception as e:
            checks["vllm_chat"] = f"error: {e}"

    return {"status": "ok" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}


@router.get("/models")
async def list_models(
    user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
):
    import httpx

    models = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{settings.vllm_embed_url}/v1/models")
            if resp.status_code == 200:
                for m in resp.json().get("data", []):
                    models.append({"id": m["id"], "type": "embedding"})
        except Exception:
            pass

        try:
            resp = await client.get(f"{settings.vllm_chat_url}/v1/models")
            if resp.status_code == 200:
                for m in resp.json().get("data", []):
                    models.append({"id": m["id"], "type": "chat"})
        except Exception:
            pass

    return {"models": models}


@router.get("/storage")
async def storage_stats(
    user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
    db: AsyncSession = Depends(get_db),
):
    # MinIO bucket stats
    minio_stats = {"object_count": 0, "total_size_bytes": 0}
    try:
        from meks.storage.client import get_minio_client
        minio_client = get_minio_client()
        objects = minio_client.list_objects(settings.minio_bucket, recursive=True)
        for obj in objects:
            minio_stats["object_count"] += 1
            minio_stats["total_size_bytes"] += obj.size or 0
    except Exception as e:
        minio_stats["error"] = str(e)

    # PostgreSQL table row counts
    pg_stats = {}
    table_names = ["users", "documents", "knowledge_bases", "document_chunks", "audit_logs", "medical_records", "sync_tasks"]
    for table in table_names:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            pg_stats[table] = result.scalar() or 0
        except Exception:
            pg_stats[table] = 0

    # Milvus collection counts
    milvus_stats = {}
    try:
        from pymilvus import utility, Collection
        collections = utility.list_collections()
        for coll_name in collections:
            try:
                coll = Collection(coll_name)
                coll.flush()
                milvus_stats[coll_name] = coll.num_entities
            except Exception:
                milvus_stats[coll_name] = -1
    except Exception as e:
        milvus_stats["error"] = str(e)

    return {
        "minio": minio_stats,
        "postgres": pg_stats,
        "milvus": milvus_stats,
    }


@router.get("/llm-settings", response_model=LLMSettingsResponse)
async def get_llm_settings(
    user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
):
    raw_key = settings.effective_cloud_api_key
    masked = None
    if raw_key:
        masked = ("*" * (len(raw_key) - 4) + raw_key[-4:]) if len(raw_key) > 4 else "****"

    return LLMSettingsResponse(
        llm_provider=settings.llm_provider,
        cloud_provider=settings.cloud_provider,
        cloud_api_key_masked=masked,
        cloud_api_base=settings.effective_cloud_api_base,
        cloud_model=settings.effective_cloud_model,
        vllm_chat_url=settings.vllm_chat_url,
        vllm_available=_is_vllm_available(),
    )


@router.put("/llm-settings")
async def update_llm_settings(
    request: LLMSettingsUpdate,
    user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "配置已接收（运行时动态生效功能将在后续版本实现）", "received": request.model_dump(exclude_none=True)}


@router.post("/llm-test")
async def test_llm_connection(
    user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
):
    try:
        provider = get_llm_provider()
        result = await asyncio.wait_for(provider.completion("Hello"), timeout=10.0)
        return {"success": True, "message": "LLM 连接正常", "response": result[:200]}
    except asyncio.TimeoutError:
        return {"success": False, "message": "LLM 响应超时（10秒）"}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {e}"}
