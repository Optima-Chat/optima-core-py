"""追踪中间件模块"""

import logging
import os
import time
from typing import Callable, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from optima_core.config import BuildInfo
from optima_core.tracing.context import clear_trace_context, set_trace_context
from optima_core.tracing.ids import generate_request_id, generate_trace_id

logger = logging.getLogger(__name__)


# Header 名称常量
TRACE_ID_HEADER = "X-Trace-ID"
REQUEST_ID_HEADER = "X-Request-ID"
PARENT_SPAN_ID_HEADER = "X-Parent-Span-ID"
DEPLOYMENT_ID_HEADER = "X-Deployment-ID"
RESPONSE_TIME_HEADER = "X-Response-Time"
SERVED_BY_HEADER = "X-Served-By"


class TracingMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件

    功能：
    1. 从 header 获取或生成 trace_id
    2. 设置日志上下文
    3. 记录请求开始/结束
    4. 在响应 header 中返回追踪信息
    """

    def __init__(
        self,
        app: Callable,
        service_name: str,
        service_short: Optional[str] = None,
        skip_paths: Optional[List[str]] = None,
        log_requests: bool = True,
    ):
        """
        Args:
            app: ASGI 应用
            service_name: 服务名称
            service_short: 服务简称（用于生成 trace_id，默认取 service_name 前 4 字符）
            skip_paths: 跳过日志记录的路径列表（如 ["/health", "/"]）
            log_requests: 是否记录请求日志
        """
        super().__init__(app)
        self.service_name = service_name
        self.service_short = service_short or service_name[:4]
        self.skip_paths = set(skip_paths or ["/health", "/", "/favicon.ico"])
        self.log_requests = log_requests
        self.build_info = BuildInfo()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 从 header 获取或生成追踪 ID
        trace_id = request.headers.get(TRACE_ID_HEADER) or generate_trace_id(self.service_short)
        request_id = generate_request_id(self.service_short)
        parent_span_id = request.headers.get(PARENT_SPAN_ID_HEADER)

        # 设置上下文
        set_trace_context(
            trace_id=trace_id,
            request_id=request_id,
            parent_span_id=parent_span_id,
        )

        start_time = time.time()
        should_log = self.log_requests and request.url.path not in self.skip_paths

        if should_log:
            logger.info(
                f"Request started: {request.method} {request.url.path}",
            )

        try:
            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000

            if should_log:
                logger.info(
                    f"Request completed: {request.method} {request.url.path} "
                    f"status={response.status_code} duration={duration_ms:.2f}ms",
                )

            # 添加响应 header
            response.headers[TRACE_ID_HEADER] = trace_id
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[RESPONSE_TIME_HEADER] = f"{duration_ms:.2f}ms"
            response.headers[SERVED_BY_HEADER] = (
                f"{self.service_name}-{self.build_info.short_commit}"
            )

            # 添加部署 ID（如果有）
            deployment_id = os.getenv("DEPLOYMENT_ID")
            if deployment_id:
                response.headers[DEPLOYMENT_ID_HEADER] = deployment_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                f"Request failed: {request.method} {request.url.path} "
                f"duration={duration_ms:.2f}ms error={str(e)}",
            )
            raise

        finally:
            # 清理上下文
            clear_trace_context()


def get_trace_headers() -> dict:
    """获取需要传递给下游服务的追踪 header

    用于在服务间调用时传递追踪信息。

    Returns:
        追踪 header 字典

    Example:
        ```python
        headers = get_trace_headers()
        response = await client.get("http://other-service/api", headers=headers)
        ```
    """
    from optima_core.tracing.context import get_request_id, get_trace_id

    headers = {}

    trace_id = get_trace_id()
    if trace_id:
        headers[TRACE_ID_HEADER] = trace_id

    request_id = get_request_id()
    if request_id:
        headers[PARENT_SPAN_ID_HEADER] = request_id

    deployment_id = os.getenv("DEPLOYMENT_ID")
    if deployment_id:
        headers[DEPLOYMENT_ID_HEADER] = deployment_id

    return headers
