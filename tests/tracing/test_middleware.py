"""追踪中间件测试"""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optima_core.tracing.middleware import (
    DEPLOYMENT_ID_HEADER,
    PARENT_SPAN_ID_HEADER,
    REQUEST_ID_HEADER,
    RESPONSE_TIME_HEADER,
    SERVED_BY_HEADER,
    TRACE_ID_HEADER,
    TracingMiddleware,
    get_trace_headers,
)
from optima_core.tracing.context import set_trace_context, clear_trace_context


@pytest.fixture
def app() -> FastAPI:
    """创建测试应用"""
    app = FastAPI()

    app.add_middleware(
        TracingMiddleware,
        service_name="test-service",
        service_short="test",
    )

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """创建测试客户端"""
    return TestClient(app, raise_server_exceptions=False)


class TestTracingMiddleware:
    """TracingMiddleware 测试"""

    def test_generates_trace_id(self, client: TestClient) -> None:
        """测试生成 trace_id"""
        response = client.get("/test")

        assert response.status_code == 200
        assert TRACE_ID_HEADER in response.headers
        assert "-test" in response.headers[TRACE_ID_HEADER]

    def test_preserves_trace_id(self, client: TestClient) -> None:
        """测试保留上游 trace_id"""
        response = client.get(
            "/test",
            headers={TRACE_ID_HEADER: "upstream-trace-123"},
        )

        assert response.status_code == 200
        assert response.headers[TRACE_ID_HEADER] == "upstream-trace-123"

    def test_generates_request_id(self, client: TestClient) -> None:
        """测试生成 request_id"""
        response = client.get("/test")

        assert response.status_code == 200
        assert REQUEST_ID_HEADER in response.headers
        assert response.headers[REQUEST_ID_HEADER].startswith("test_")

    def test_response_time_header(self, client: TestClient) -> None:
        """测试响应时间 header"""
        response = client.get("/test")

        assert response.status_code == 200
        assert RESPONSE_TIME_HEADER in response.headers
        assert response.headers[RESPONSE_TIME_HEADER].endswith("ms")

    def test_served_by_header(self, client: TestClient) -> None:
        """测试 served-by header"""
        response = client.get("/test")

        assert response.status_code == 200
        assert SERVED_BY_HEADER in response.headers
        assert "test-service" in response.headers[SERVED_BY_HEADER]

    def test_deployment_id_header(self, client: TestClient) -> None:
        """测试 deployment_id header"""
        os.environ["DEPLOYMENT_ID"] = "blue"
        try:
            response = client.get("/test")

            assert response.status_code == 200
            assert response.headers.get(DEPLOYMENT_ID_HEADER) == "blue"
        finally:
            del os.environ["DEPLOYMENT_ID"]

    def test_no_deployment_id_when_not_set(self, client: TestClient) -> None:
        """测试未设置时不添加 deployment_id"""
        if "DEPLOYMENT_ID" in os.environ:
            del os.environ["DEPLOYMENT_ID"]

        response = client.get("/test")

        assert response.status_code == 200
        assert DEPLOYMENT_ID_HEADER not in response.headers

    def test_parent_span_id_passed(self, client: TestClient) -> None:
        """测试传递 parent_span_id"""
        response = client.get(
            "/test",
            headers={PARENT_SPAN_ID_HEADER: "parent-span-123"},
        )

        assert response.status_code == 200
        # parent_span_id 不会在响应中返回，但会在日志上下文中使用

    def test_error_handling(self, client: TestClient) -> None:
        """测试错误处理"""
        response = client.get("/error")

        assert response.status_code == 500


class TestSkipPaths:
    """跳过路径测试"""

    def test_health_path_skipped_by_default(self, app: FastAPI) -> None:
        """测试 /health 路径默认跳过"""
        # 中间件已配置默认跳过 /health
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        # 仍然添加追踪 header
        assert TRACE_ID_HEADER in response.headers

    def test_custom_skip_paths(self) -> None:
        """测试自定义跳过路径"""
        app = FastAPI()
        app.add_middleware(
            TracingMiddleware,
            service_name="test-service",
            skip_paths=["/health", "/metrics", "/custom"],
        )

        @app.get("/custom")
        async def custom_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/custom")

        assert response.status_code == 200


class TestGetTraceHeaders:
    """get_trace_headers 测试"""

    def setup_method(self) -> None:
        """每个测试前清理上下文"""
        clear_trace_context()

    def teardown_method(self) -> None:
        """每个测试后清理上下文"""
        clear_trace_context()
        if "DEPLOYMENT_ID" in os.environ:
            del os.environ["DEPLOYMENT_ID"]

    def test_empty_when_no_context(self) -> None:
        """测试无上下文时返回空"""
        headers = get_trace_headers()
        assert headers == {}

    def test_includes_trace_id(self) -> None:
        """测试包含 trace_id"""
        set_trace_context(trace_id="trace-123")

        headers = get_trace_headers()

        assert headers[TRACE_ID_HEADER] == "trace-123"

    def test_includes_parent_span_id(self) -> None:
        """测试包含 parent_span_id（来自 request_id）"""
        set_trace_context(trace_id="trace-123", request_id="req-456")

        headers = get_trace_headers()

        assert headers[TRACE_ID_HEADER] == "trace-123"
        assert headers[PARENT_SPAN_ID_HEADER] == "req-456"

    def test_includes_deployment_id(self) -> None:
        """测试包含 deployment_id"""
        os.environ["DEPLOYMENT_ID"] = "green"
        set_trace_context(trace_id="trace-123")

        headers = get_trace_headers()

        assert headers[DEPLOYMENT_ID_HEADER] == "green"
