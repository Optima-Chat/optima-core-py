"""调试端点模块"""

import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, Header, HTTPException

from optima_core.config import BuildInfo, get_settings

# 敏感关键词列表
SENSITIVE_KEYWORDS = [
    "KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "CREDENTIAL",
    "PRIVATE",
    "AUTH",
    "API_KEY",
    "ACCESS",
    "BEARER",
]

# 需要显示的环境变量前缀
RELEVANT_PREFIXES = [
    "APP_",
    "DATABASE",
    "REDIS",
    "MINIO",
    "OAUTH",
    "STRIPE",
    "CORS",
    "LOG_",
    "DEBUG",
    "ENABLE_",
    "INFISICAL",
    "ENVIRONMENT",
    "SERVICE",
]


def _is_sensitive(key: str) -> bool:
    """判断是否是敏感变量"""
    key_upper = key.upper()
    return any(kw in key_upper for kw in SENSITIVE_KEYWORDS)


def _mask_value(key: str, value: str) -> str:
    """脱敏处理"""
    if not value:
        return "<not set>"

    if _is_sensitive(key):
        if len(value) > 8:
            return f"{value[:2]}...{value[-2:]} ({len(value)} chars)"
        return f"****** ({len(value)} chars)"

    # URL 中的密码脱敏
    url_pattern = r"://([^:]+):([^@]+)@"
    if re.search(url_pattern, value):
        return re.sub(url_pattern, r"://\1:***@", value)

    return value


def _is_relevant_env(key: str) -> bool:
    """判断是否是需要显示的环境变量"""
    return any(key.startswith(prefix) for prefix in RELEVANT_PREFIXES)


def _get_masked_config() -> Dict[str, str]:
    """获取脱敏后的配置"""
    config = {}
    for key, value in sorted(os.environ.items()):
        if _is_relevant_env(key):
            config[key] = _mask_value(key, value)
    return config


def _get_key_dependencies() -> Dict[str, str]:
    """获取关键依赖版本"""
    deps = {}

    modules = [
        ("fastapi", "fastapi"),
        ("pydantic", "pydantic"),
        ("sqlalchemy", "sqlalchemy"),
        ("httpx", "httpx"),
        ("redis", "redis"),
        ("asyncpg", "asyncpg"),
    ]

    for name, module_name in modules:
        try:
            module = __import__(module_name)
            deps[name] = getattr(module, "__version__", "unknown")
        except ImportError:
            pass

    return deps


# 启动时间记录
_startup_time: Optional[datetime] = None


def _get_startup_time() -> datetime:
    """获取启动时间"""
    global _startup_time
    if _startup_time is None:
        _startup_time = datetime.now(timezone.utc)
    return _startup_time


def setup_debug_routes(
    app: FastAPI,
    prefix: str = "/debug",
    debug_key_header: str = "X-Debug-Key",
    require_key_for_info: bool = False,
) -> APIRouter:
    """设置调试端点

    Args:
        app: FastAPI 应用
        prefix: 路由前缀
        debug_key_header: 认证 header 名称
        require_key_for_info: /debug/info 是否需要认证

    Returns:
        APIRouter 实例
    """
    router = APIRouter(prefix=prefix, tags=["debug"])

    def _check_debug_key(key: Optional[str]) -> None:
        """验证调试密钥"""
        settings = get_settings()
        expected_key = settings.debug_key

        if not expected_key:
            raise HTTPException(
                status_code=503,
                detail="Debug endpoints not configured. Set DEBUG_KEY environment variable.",
            )

        if key != expected_key:
            raise HTTPException(status_code=403, detail="Invalid debug key")

    @router.get("/info")
    async def debug_info(
        x_debug_key: Optional[str] = Header(None, alias=debug_key_header),
    ) -> Dict[str, Any]:
        """获取服务运行时信息"""
        if require_key_for_info:
            _check_debug_key(x_debug_key)

        build_info = BuildInfo()
        settings = get_settings()
        startup_time = _get_startup_time()
        uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()

        return {
            "build": build_info.to_dict(),
            "runtime": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "environment": settings.environment,
                "debug_mode": settings.debug,
                "log_level": settings.log_level,
                "log_format": settings.log_format,
            },
            "startup_time": startup_time.isoformat(),
            "uptime_seconds": int(uptime),
            "dependencies": _get_key_dependencies(),
        }

    @router.get("/config")
    async def debug_config(
        x_debug_key: Optional[str] = Header(None, alias=debug_key_header),
    ) -> Dict[str, Any]:
        """获取脱敏后的配置信息（需要认证）"""
        _check_debug_key(x_debug_key)

        settings = get_settings()

        return {
            "config": _get_masked_config(),
            "infisical_enabled": bool(os.getenv("INFISICAL_PROJECT_ID")),
            "config_source": "infisical" if os.getenv("USE_INFISICAL_CLI") else "environment",
            "environment": settings.environment,
        }

    app.include_router(router)
    return router
