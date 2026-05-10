from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meks.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from meks.models.base import init_db
    from meks.vectordb.client import init_milvus
    from meks.storage.client import init_minio

    await init_db()
    init_milvus()
    init_minio()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from meks.api.router import api_router

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
