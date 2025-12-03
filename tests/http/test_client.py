"""HTTP 客户端测试"""

import os
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from optima_core.http.client import TracedHttpClient
from optima_core.tracing.context import clear_trace_context, set_trace_context
from optima_core.tracing.middleware import (
    DEPLOYMENT_ID_HEADER,
    PARENT_SPAN_ID_HEADER,
    TRACE_ID_HEADER,
)


class TestTracedHttpClient:
    """TracedHttpClient 测试"""

    def setup_method(self) -> None:
        """每个测试前清理上下文"""
        clear_trace_context()

    def teardown_method(self) -> None:
        """每个测试后清理上下文"""
        clear_trace_context()
        if "DEPLOYMENT_ID" in os.environ:
            del os.environ["DEPLOYMENT_ID"]

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """测试上下文管理器"""
        async with TracedHttpClient() as client:
            assert client._client is None  # 延迟初始化

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """测试关闭客户端"""
        client = TracedHttpClient()
        # 初始化客户端
        await client._get_client()
        assert client._client is not None

        await client.close()
        assert client._client is None

    def test_merge_headers_empty_context(self) -> None:
        """测试无上下文时合并 header"""
        client = TracedHttpClient()
        headers = client._merge_headers()
        assert headers == {}

    def test_merge_headers_with_trace_context(self) -> None:
        """测试有追踪上下文时合并 header"""
        set_trace_context(trace_id="trace-123", request_id="req-456")
        client = TracedHttpClient()

        headers = client._merge_headers()

        assert headers[TRACE_ID_HEADER] == "trace-123"
        assert headers[PARENT_SPAN_ID_HEADER] == "req-456"

    def test_merge_headers_with_deployment_id(self) -> None:
        """测试有 deployment_id 时合并 header"""
        os.environ["DEPLOYMENT_ID"] = "blue"
        set_trace_context(trace_id="trace-123")
        client = TracedHttpClient()

        headers = client._merge_headers()

        assert headers[DEPLOYMENT_ID_HEADER] == "blue"

    def test_merge_headers_custom_override(self) -> None:
        """测试自定义 header 覆盖"""
        set_trace_context(trace_id="trace-123")
        client = TracedHttpClient()

        headers = client._merge_headers({TRACE_ID_HEADER: "custom-trace"})

        assert headers[TRACE_ID_HEADER] == "custom-trace"

    def test_merge_headers_add_custom(self) -> None:
        """测试添加自定义 header"""
        set_trace_context(trace_id="trace-123")
        client = TracedHttpClient()

        headers = client._merge_headers({"Authorization": "Bearer token"})

        assert headers[TRACE_ID_HEADER] == "trace-123"
        assert headers["Authorization"] == "Bearer token"

    @pytest.mark.asyncio
    async def test_get_client_creates_once(self) -> None:
        """测试客户端只创建一次"""
        client = TracedHttpClient()

        client1 = await client._get_client()
        client2 = await client._get_client()

        assert client1 is client2
        await client.close()

    @pytest.mark.asyncio
    async def test_base_url_config(self) -> None:
        """测试 base_url 配置"""
        client = TracedHttpClient(base_url="http://test.local")
        internal = await client._get_client()

        assert str(internal.base_url) == "http://test.local"
        await client.close()

    @pytest.mark.asyncio
    async def test_timeout_config(self) -> None:
        """测试超时配置"""
        client = TracedHttpClient(timeout=15.0)
        internal = await client._get_client()

        assert internal.timeout.connect == 15.0
        await client.close()

    @pytest.mark.asyncio
    async def test_request_method(self) -> None:
        """测试 request 方法注入 header"""
        set_trace_context(trace_id="trace-123", request_id="req-456")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            client = TracedHttpClient()
            await client._get_client()  # 初始化
            response = await client.request("GET", "http://test.local/api")

            # 验证调用参数
            call_kwargs = mock_request.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert headers.get(TRACE_ID_HEADER) == "trace-123"
            assert headers.get(PARENT_SPAN_ID_HEADER) == "req-456"

            await client.close()

    @pytest.mark.asyncio
    async def test_get_method(self) -> None:
        """测试 GET 方法"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with TracedHttpClient() as client:
                await client._get_client()
                await client.get("http://test.local/api")

                mock_request.assert_called_once()
                assert mock_request.call_args.kwargs["method"] == "GET"

    @pytest.mark.asyncio
    async def test_post_method(self) -> None:
        """测试 POST 方法"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with TracedHttpClient() as client:
                await client._get_client()
                await client.post("http://test.local/api", json={"key": "value"})

                mock_request.assert_called_once()
                assert mock_request.call_args.kwargs["method"] == "POST"

    @pytest.mark.asyncio
    async def test_put_method(self) -> None:
        """测试 PUT 方法"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with TracedHttpClient() as client:
                await client._get_client()
                await client.put("http://test.local/api/1")

                mock_request.assert_called_once()
                assert mock_request.call_args.kwargs["method"] == "PUT"

    @pytest.mark.asyncio
    async def test_patch_method(self) -> None:
        """测试 PATCH 方法"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with TracedHttpClient() as client:
                await client._get_client()
                await client.patch("http://test.local/api/1")

                mock_request.assert_called_once()
                assert mock_request.call_args.kwargs["method"] == "PATCH"

    @pytest.mark.asyncio
    async def test_delete_method(self) -> None:
        """测试 DELETE 方法"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with TracedHttpClient() as client:
                await client._get_client()
                await client.delete("http://test.local/api/1")

                mock_request.assert_called_once()
                assert mock_request.call_args.kwargs["method"] == "DELETE"
