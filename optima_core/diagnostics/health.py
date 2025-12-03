"""健康检查模块"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional, Union

from fastapi import FastAPI

from optima_core.config import BuildInfo, get_settings

# 健康检查函数类型
HealthCheckFunc = Union[Callable[[], bool], Callable[[], Coroutine[Any, Any, bool]]]


class HealthChecker:
    """统一的健康检查器"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.start_time = time.time()
        self.build_info = BuildInfo()
        self._checks: Dict[str, HealthCheckFunc] = {}

    def register_check(self, name: str, check_func: HealthCheckFunc) -> None:
        """注册健康检查项"""
        self._checks[name] = check_func

    async def run_checks(self, timeout: float = 5.0) -> Dict[str, Any]:
        """运行所有健康检查"""
        results: Dict[str, Any] = {}
        overall_healthy = True

        for name, check_func in self._checks.items():
            start = time.time()
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await asyncio.wait_for(check_func(), timeout=timeout)
                else:
                    result = check_func()

                latency_ms = round((time.time() - start) * 1000, 2)
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "latency_ms": latency_ms,
                }
                if not result:
                    overall_healthy = False

            except asyncio.TimeoutError:
                results[name] = {"status": "timeout", "error": f"Check timed out ({timeout}s)"}
                overall_healthy = False
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
                overall_healthy = False

        settings = get_settings()

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "service": self.service_name,
            "version": self.build_info.version,
            "git_commit": self.build_info.short_commit,
            "environment": settings.environment,
            "uptime_seconds": int(time.time() - self.start_time),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": results,
        }

    @property
    def uptime_seconds(self) -> int:
        """返回运行时间（秒）"""
        return int(time.time() - self.start_time)


# 全局健康检查器实例
_health_checkers: Dict[str, HealthChecker] = {}


def get_health_checker(service_name: str) -> HealthChecker:
    """获取健康检查器（单例）"""
    if service_name not in _health_checkers:
        _health_checkers[service_name] = HealthChecker(service_name)
    return _health_checkers[service_name]


def setup_health_routes(
    app: FastAPI,
    service_name: str,
    checks: Optional[Dict[str, HealthCheckFunc]] = None,
) -> HealthChecker:
    """设置健康检查路由

    Args:
        app: FastAPI 应用
        service_name: 服务名称
        checks: 健康检查函数字典，如 {"database": check_db, "redis": check_redis}

    Returns:
        HealthChecker 实例
    """
    health_checker = get_health_checker(service_name)

    if checks:
        for name, check_func in checks.items():
            health_checker.register_check(name, check_func)

    @app.get("/health", tags=["diagnostics"])
    async def health_check() -> Dict[str, Any]:
        """健康检查端点"""
        return await health_checker.run_checks()

    @app.get("/", tags=["diagnostics"])
    async def root() -> Dict[str, str]:
        """根路径"""
        return {
            "service": service_name,
            "version": health_checker.build_info.version,
            "status": "running",
        }

    return health_checker


# 预置的健康检查函数工厂


def create_health_check_database(get_engine: Callable[[], Any]) -> HealthCheckFunc:
    """创建数据库健康检查函数

    Args:
        get_engine: 返回 SQLAlchemy AsyncEngine 的函数

    Example:
        ```python
        from myapp.database import get_engine
        check_db = create_health_check_database(get_engine)
        ```
    """

    async def check() -> bool:
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    return check


def create_health_check_redis(get_client: Callable[[], Any]) -> HealthCheckFunc:
    """创建 Redis 健康检查函数

    Args:
        get_client: 返回 Redis 客户端的函数

    Example:
        ```python
        from myapp.cache import get_redis_client
        check_redis = create_health_check_redis(get_redis_client)
        ```
    """

    async def check() -> bool:
        try:
            client = get_client()
            await client.ping()
            return True
        except Exception:
            return False

    return check


def create_health_check_http(
    url: str, timeout: float = 5.0, expected_status: int = 200
) -> HealthCheckFunc:
    """创建 HTTP 健康检查函数

    Args:
        url: 健康检查 URL
        timeout: 超时时间
        expected_status: 期望的状态码

    Example:
        ```python
        check_auth = create_health_check_http("http://user-auth:8000/health")
        ```
    """

    async def check() -> bool:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout)
                return response.status_code == expected_status
        except Exception:
            return False

    return check
