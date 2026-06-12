"""认证 API 测试：登录、Token 刷新、/me 端点。"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_refresh_token, make_token


class TestLogin:
    async def test_login_success(self, async_client: AsyncClient, researcher_user):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "researcher_test", "password": "pass123456"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"]

    async def test_login_wrong_password(self, async_client: AsyncClient, researcher_user):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "researcher_test", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.json()["detail"]

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "no_such_user", "password": "pass123456"},
        )
        assert resp.status_code == 401

    async def test_login_disabled_user(self, async_client: AsyncClient, disabled_user):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "disabled_test", "password": "pass123456"},
        )
        assert resp.status_code == 401
        assert "禁用" in resp.json()["detail"]

    async def test_login_updates_last_login(self, async_client: AsyncClient, doctor_user, db_session: AsyncSession):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "doctor_test", "password": "pass123456"},
        )
        assert resp.status_code == 200
        await db_session.refresh(doctor_user)
        assert doctor_user.last_login is not None


class TestTokenRefresh:
    async def test_refresh_success(self, async_client: AsyncClient, researcher_user):
        token = make_refresh_token(researcher_user)
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert resp.status_code == 401
        assert "无效的刷新令牌" in resp.json()["detail"]

    async def test_refresh_with_access_token_fails(self, async_client: AsyncClient, researcher_user):
        # 使用 access token 而非 refresh token，应返回 401
        token = make_token(researcher_user)
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token},
        )
        assert resp.status_code == 401

    async def test_refresh_disabled_user(self, async_client: AsyncClient, disabled_user):
        token = make_refresh_token(disabled_user)
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token},
        )
        assert resp.status_code == 401


class TestGetMe:
    async def test_get_me_success(self, async_client: AsyncClient, admin_user):
        token = make_token(admin_user)
        resp = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin_test"
        assert data["role"] == "admin"

    async def test_get_me_no_token(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/auth/me")
        assert resp.status_code == 403  # HTTPBearer 缺少凭证返回 403

    async def test_get_me_invalid_token(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401
