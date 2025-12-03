"""健康检查测试"""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optima_core.diagnostics import HealthChecker, setup_health_routes


class TestHealthChecker:
    """HealthChecker 测试"""

    def test_init(self) -> None:
        """测试初始化"""
        checker = HealthChecker("test-service")
        assert checker.service_name == "test-service"
        assert checker.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_run_checks_empty(self) -> None:
        """测试无检查项时的运行"""
        checker = HealthChecker("test-service")
        result = await checker.run_checks()

        assert result["status"] == "healthy"
        assert result["service"] == "test-service"
        assert result["checks"] == {}

    @pytest.mark.asyncio
    async def test_run_checks_sync_pass(self) -> None:
        """测试同步检查通过"""
        checker = HealthChecker("test-service")
        checker.register_check("sync_check", lambda: True)

        result = await checker.run_checks()

        assert result["status"] == "healthy"
        assert result["checks"]["sync_check"]["status"] == "healthy"
        assert "latency_ms" in result["checks"]["sync_check"]

    @pytest.mark.asyncio
    async def test_run_checks_sync_fail(self) -> None:
        """测试同步检查失败"""
        checker = HealthChecker("test-service")
        checker.register_check("sync_check", lambda: False)

        result = await checker.run_checks()

        assert result["status"] == "degraded"
        assert result["checks"]["sync_check"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_run_checks_async_pass(self) -> None:
        """测试异步检查通过"""
        checker = HealthChecker("test-service")

        async def async_check() -> bool:
            return True

        checker.register_check("async_check", async_check)

        result = await checker.run_checks()

        assert result["status"] == "healthy"
        assert result["checks"]["async_check"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_run_checks_exception(self) -> None:
        """测试检查抛出异常"""
        checker = HealthChecker("test-service")

        def failing_check() -> bool:
            raise ValueError("Test error")

        checker.register_check("failing_check", failing_check)

        result = await checker.run_checks()

        assert result["status"] == "degraded"
        assert result["checks"]["failing_check"]["status"] == "error"
        assert "Test error" in result["checks"]["failing_check"]["error"]

    @pytest.mark.asyncio
    async def test_run_checks_with_version(self) -> None:
        """测试返回版本信息"""
        os.environ["APP_VERSION"] = "1.2.3"
        os.environ["GIT_COMMIT"] = "abc1234567890"

        checker = HealthChecker("test-service")
        result = await checker.run_checks()

        assert result["version"] == "1.2.3"
        assert result["git_commit"] == "abc1234"  # short commit


class TestSetupHealthRoutes:
    """setup_health_routes 测试"""

    def test_health_endpoint(self, app: FastAPI) -> None:
        """测试 /health 端点"""
        setup_health_routes(app, service_name="test-service")
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "test-service"
        assert data["status"] == "healthy"

    def test_root_endpoint(self, app: FastAPI) -> None:
        """测试 / 端点"""
        setup_health_routes(app, service_name="test-service")
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "test-service"
        assert data["status"] == "running"

    def test_health_with_checks(self, app: FastAPI) -> None:
        """测试带检查项的健康检查"""
        setup_health_routes(
            app,
            service_name="test-service",
            checks={
                "always_pass": lambda: True,
                "always_fail": lambda: False,
            },
        )
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["always_pass"]["status"] == "healthy"
        assert data["checks"]["always_fail"]["status"] == "unhealthy"
