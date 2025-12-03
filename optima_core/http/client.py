"""带追踪的 HTTP 客户端模块"""

import logging
from typing import Any, Dict, Optional

import httpx

from optima_core.tracing.middleware import get_trace_headers

logger = logging.getLogger(__name__)


class TracedHttpClient:
    """自动传递追踪信息的 HTTP 客户端

    使用方法：

    ```python
    # 作为上下文管理器
    async with TracedHttpClient() as client:
        response = await client.get("http://other-service/api/data")

    # 或者手动管理
    client = TracedHttpClient()
    response = await client.get("http://other-service/api/data")
    await client.close()
    ```
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        **kwargs: Any,
    ):
        """
        Args:
            base_url: 基础 URL
            timeout: 请求超时时间（秒）
            **kwargs: 传递给 httpx.AsyncClient 的其他参数
        """
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = base_url
        self._timeout = timeout
        self._kwargs = kwargs

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建客户端"""
        if self._client is None:
            kwargs: Dict[str, Any] = {
                "timeout": self._timeout,
                **self._kwargs,
            }
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "TracedHttpClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _merge_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """合并追踪 header 和用户提供的 header"""
        trace_headers = get_trace_headers()
        if headers:
            trace_headers.update(headers)
        return trace_headers

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送请求

        Args:
            method: HTTP 方法
            url: URL
            headers: 额外的 header
            **kwargs: 传递给 httpx 的其他参数

        Returns:
            HTTP 响应
        """
        client = await self._get_client()
        merged_headers = self._merge_headers(headers)

        logger.debug(f"Sending {method} request to {url}")

        response = await client.request(
            method=method,
            url=url,
            headers=merged_headers,
            **kwargs,
        )

        logger.debug(f"Received response: status={response.status_code}")

        return response

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送 GET 请求"""
        return await self.request("GET", url, headers=headers, **kwargs)

    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送 POST 请求"""
        return await self.request("POST", url, headers=headers, **kwargs)

    async def put(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送 PUT 请求"""
        return await self.request("PUT", url, headers=headers, **kwargs)

    async def patch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送 PATCH 请求"""
        return await self.request("PATCH", url, headers=headers, **kwargs)

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送 DELETE 请求"""
        return await self.request("DELETE", url, headers=headers, **kwargs)
