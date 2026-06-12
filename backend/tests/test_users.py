"""用户管理 API 测试：分页、创建冲突、权限控制。"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from meks.models.user import User, UserRole
from tests.conftest import make_token


class TestListUsers:
    async def test_admin_can_list_users(
        self, async_client: AsyncClient, admin_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

    async def test_non_admin_cannot_list_users(
        self, async_client: AsyncClient, researcher_user: User
    ):
        token = make_token(researcher_user)
        resp = await async_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_doctor_cannot_list_users(
        self, async_client: AsyncClient, doctor_user: User
    ):
        token = make_token(doctor_user)
        resp = await async_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_pagination_page_size(
        self, async_client: AsyncClient, admin_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.get(
            "/api/v1/users?page=1&page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1

    async def test_pagination_page_2(
        self, async_client: AsyncClient, admin_user: User, db_session: AsyncSession
    ):
        # 创建额外用户确保有多页
        for i in range(3):
            from meks.core.security import hash_password
            u = User(
                id=uuid.uuid4(),
                username=f"paginate_user_{i}",
                email=f"paginate{i}@test.com",
                hashed_password=hash_password("pass123"),
                full_name=f"分页用户{i}",
                role=UserRole.viewer,
                is_active=True,
            )
            db_session.add(u)
        await db_session.commit()

        token = make_token(admin_user)
        resp = await async_client.get(
            "/api/v1/users?page=1&page_size=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 4

    async def test_invalid_page_size_rejected(
        self, async_client: AsyncClient, admin_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.get(
            "/api/v1/users?page_size=200",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


class TestCreateUser:
    async def test_admin_can_create_user(
        self, async_client: AsyncClient, admin_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.post(
            "/api/v1/users",
            json={
                "username": "new_user_unique",
                "email": "newuser_unique@test.com",
                "password": "password123",
                "full_name": "新用户",
                "role": "doctor",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "new_user_unique"
        assert data["role"] == "doctor"

    async def test_duplicate_username_conflict(
        self, async_client: AsyncClient, admin_user: User, researcher_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.post(
            "/api/v1/users",
            json={
                "username": "researcher_test",  # 已存在的用户名
                "email": "totally_new@test.com",
                "password": "password123",
                "full_name": "重复用户名",
                "role": "doctor",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    async def test_duplicate_email_conflict(
        self, async_client: AsyncClient, admin_user: User, researcher_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.post(
            "/api/v1/users",
            json={
                "username": "brand_new_name",
                "email": "researcher@test.com",  # 已存在的邮箱
                "password": "password123",
                "full_name": "重复邮箱",
                "role": "doctor",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    async def test_non_admin_cannot_create_user(
        self, async_client: AsyncClient, researcher_user: User
    ):
        token = make_token(researcher_user)
        resp = await async_client.post(
            "/api/v1/users",
            json={
                "username": "new_user2",
                "email": "new2@test.com",
                "password": "password123",
                "full_name": "越权创建",
                "role": "doctor",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestGetUser:
    async def test_admin_can_get_user(
        self, async_client: AsyncClient, admin_user: User, doctor_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.get(
            f"/api/v1/users/{doctor_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "doctor_test"

    async def test_get_nonexistent_user(
        self, async_client: AsyncClient, admin_user: User
    ):
        token = make_token(admin_user)
        resp = await async_client.get(
            f"/api/v1/users/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestDeleteUser:
    async def test_admin_can_disable_user(
        self, async_client: AsyncClient, admin_user: User, db_session: AsyncSession
    ):
        from meks.core.security import hash_password
        target = User(
            id=uuid.uuid4(),
            username="to_disable",
            email="todisable@test.com",
            hashed_password=hash_password("pass123"),
            full_name="待禁用用户",
            role=UserRole.viewer,
            is_active=True,
        )
        db_session.add(target)
        await db_session.commit()

        token = make_token(admin_user)
        resp = await async_client.delete(
            f"/api/v1/users/{target.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        await db_session.refresh(target)
        assert not target.is_active
