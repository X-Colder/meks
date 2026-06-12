"""测试配置：提供共享的 fixtures，使用 SQLite 内存数据库避免依赖 PostgreSQL。"""
import os
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# 在导入应用之前设置测试环境变量
os.environ.setdefault("MEKS_SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("MEKS_DEBUG", "true")
os.environ.setdefault("MEKS_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from meks.core.security import create_access_token, create_refresh_token, hash_password
from meks.models.base import Base
from meks.models.knowledge_base import KBType, KnowledgeBase, Visibility
from meks.models.user import User, UserRole

# 使用 SQLite 内存数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """创建共享的测试数据库引擎（整个测试会话复用）。"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """每个测试函数使用独立事务，测试结束后回滚保持隔离。"""
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username="admin_test",
        email="admin@test.com",
        hashed_password=hash_password("admin123456"),
        full_name="测试管理员",
        role=UserRole.admin,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def researcher_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username="researcher_test",
        email="researcher@test.com",
        hashed_password=hash_password("pass123456"),
        full_name="测试研究员",
        role=UserRole.researcher,
        department="研究部",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def doctor_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username="doctor_test",
        email="doctor@test.com",
        hashed_password=hash_password("pass123456"),
        full_name="测试医生",
        role=UserRole.doctor,
        department="内科",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username="viewer_test",
        email="viewer@test.com",
        hashed_password=hash_password("pass123456"),
        full_name="测试查看者",
        role=UserRole.viewer,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def disabled_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username="disabled_test",
        email="disabled@test.com",
        hashed_password=hash_password("pass123456"),
        full_name="已禁用用户",
        role=UserRole.doctor,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def make_token(user: User) -> str:
    return create_access_token(user.id, user.role.value)


def make_refresh_token(user: User) -> str:
    return create_refresh_token(user.id)


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession, engine):
    """创建 FastAPI AsyncClient，覆盖数据库依赖并 mock 外部服务。"""
    # mock 外部依赖，避免测试时连接真实服务
    with (
        patch("meks.vectordb.client.init_milvus"),
        patch("meks.storage.client.init_minio"),
        patch("meks.vectordb.collections.create_collection"),
        patch("meks.vectordb.collections.drop_collection"),
    ):
        from meks.main import create_app
        from meks.models.base import get_db

        app = create_app()

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client

        app.dependency_overrides.clear()
