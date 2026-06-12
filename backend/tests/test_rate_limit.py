"""限流中间件测试：正常请求通过、超过限制返回 429。"""
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from meks.core.rate_limit import RateLimitMiddleware


def _make_app_with_limit(limit: int) -> FastAPI:
    """创建一个带限流中间件的最小 FastAPI 应用，用于测试。"""
    app = FastAPI()

    # 手动构造中间件并注入自定义限制
    with patch("meks.core.rate_limit.settings") as mock_settings:
        mock_settings.rate_limit_per_minute = limit
        app.add_middleware(RateLimitMiddleware)

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    return app


class TestRateLimitMiddleware:
    def test_requests_within_limit_pass(self):
        app = _make_app_with_limit(5)
        client = TestClient(app, raise_server_exceptions=False)

        for i in range(5):
            resp = client.get("/ping")
            assert resp.status_code == 200, f"第 {i+1} 次请求应通过"

    def test_request_exceeding_limit_returns_429(self):
        app = _make_app_with_limit(3)
        client = TestClient(app, raise_server_exceptions=False)

        for i in range(3):
            resp = client.get("/ping")
            assert resp.status_code == 200

        resp = client.get("/ping")
        assert resp.status_code == 429
        assert "请求过于频繁" in resp.json()["detail"]

    def test_expired_requests_slide_out_of_window(self):
        """过期记录清理后，新请求应能通过。"""
        app = _make_app_with_limit(2)
        client = TestClient(app, raise_server_exceptions=False)

        fake_now = time.time()
        with patch("meks.core.rate_limit.time") as mock_time:
            mock_time.time.return_value = fake_now

            # 发送 2 次请求，达到限制
            client.get("/ping")
            client.get("/ping")

            # 第 3 次超限
            resp = client.get("/ping")
            assert resp.status_code == 429

            # 时间前进 61 秒（超出 60 秒窗口）
            mock_time.time.return_value = fake_now + 61

            # 现在应能再次通过
            resp = client.get("/ping")
            assert resp.status_code == 200

    def test_different_ips_counted_separately(self):
        """不同 IP 的请求应独立计数。"""
        app = _make_app_with_limit(1)

        from starlette.testclient import TestClient as StarletteClient

        client = TestClient(app, raise_server_exceptions=False)

        # 第一次请求（127.0.0.1）
        resp = client.get("/ping")
        assert resp.status_code == 200

        # 第二次同 IP 超限
        resp = client.get("/ping")
        assert resp.status_code == 429


class TestRateLimitMiddlewareUnit:
    async def test_dispatch_allows_under_limit(self):
        """单元测试 dispatch 方法。"""
        from meks.core.rate_limit import RateLimitMiddleware

        with patch("meks.core.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_per_minute = 10
            middleware = RateLimitMiddleware(app=None)  # type: ignore

        call_next_called = False

        async def call_next(req):
            nonlocal call_next_called
            call_next_called = True
            return JSONResponse({"ok": True})

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }

        class FakeClient:
            host = "10.0.0.1"

        from starlette.requests import Request as StarletteRequest
        request = StarletteRequest(scope)
        request._client = FakeClient()  # type: ignore

        response = await middleware.dispatch(request, call_next)
        assert call_next_called
        assert response.status_code == 200

    async def test_dispatch_blocks_over_limit(self):
        from meks.core.rate_limit import RateLimitMiddleware

        with patch("meks.core.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_per_minute = 2
            middleware = RateLimitMiddleware(app=None)  # type: ignore

        async def call_next(req):
            return JSONResponse({"ok": True})

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }

        class FakeClient:
            host = "192.168.1.1"

        from starlette.requests import Request as StarletteRequest

        for _ in range(2):
            request = StarletteRequest(scope)
            request._client = FakeClient()  # type: ignore
            await middleware.dispatch(request, call_next)

        request = StarletteRequest(scope)
        request._client = FakeClient()  # type: ignore
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 429
