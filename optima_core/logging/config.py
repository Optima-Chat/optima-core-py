"""日志配置模块"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from optima_core.config import BuildInfo, get_settings

# 第三方库日志抑制配置
SUPPRESSED_LOGGERS = {
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "uvicorn.access": logging.WARNING,
    "sqlalchemy.engine": logging.WARNING,
    "aiosqlite": logging.WARNING,
    "anyio": logging.WARNING,
    "mcp": logging.WARNING,
    "asyncio": logging.WARNING,
    "watchfiles.main": logging.WARNING,
}


class JSONFormatter(logging.Formatter):
    """结构化 JSON 日志格式化器"""

    def __init__(self, service_name: str, version: str, environment: str, git_commit: str):
        super().__init__()
        self.service_name = service_name
        self.version = version
        self.environment = environment
        self.git_commit = git_commit

    def format(self, record: logging.LogRecord) -> str:
        # 从 tracing context 获取追踪信息
        from optima_core.tracing import get_trace_id, get_request_id, get_parent_span_id

        log_data: Dict[str, Any] = {
            # 时间戳（ISO 8601）
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # 日志级别
            "level": record.levelname,
            # 服务信息
            "service": self.service_name,
            "version": self.version,
            "environment": self.environment,
            "git_commit": self.git_commit,
            # 日志内容
            "message": record.getMessage(),
            "logger": record.name,
            # 追踪信息
            "trace_id": get_trace_id(),
            "request_id": get_request_id(),
            "parent_span_id": get_parent_span_id(),
        }

        # 添加部署 ID（如果有）
        settings = get_settings()
        if settings.deployment_id:
            log_data["deployment_id"] = settings.deployment_id

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # 添加额外字段
        if hasattr(record, "extra_data") and record.extra_data:
            log_data["extra"] = record.extra_data

        # 移除 None 值
        log_data = {k: v for k, v in log_data.items() if v is not None}

        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """可读的文本日志格式化器（用于本地开发）"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        from optima_core.tracing import get_trace_id

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trace_id = get_trace_id()
        trace_suffix = f" | trace_id={trace_id}" if trace_id else ""

        message = f"{timestamp} [{record.levelname}] {self.service_name} - {record.getMessage()}{trace_suffix}"

        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


def configure_logging(
    service_name: str,
    version: Optional[str] = None,
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    suppress_third_party: bool = True,
) -> None:
    """配置结构化日志

    Args:
        service_name: 服务名称
        version: 版本号（默认从环境变量读取）
        log_level: 日志级别（默认从环境变量读取）
        log_format: 日志格式 json/text（默认从环境变量读取）
        suppress_third_party: 是否抑制第三方库的日志
    """
    build_info = BuildInfo()
    settings = get_settings()

    # 使用参数或默认值
    version = version or build_info.version
    log_level = log_level or settings.log_level
    log_format = log_format or settings.log_format

    # 获取日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 创建 handler
    handler = logging.StreamHandler(sys.stdout)

    # 选择格式化器
    if log_format == "json":
        handler.setFormatter(
            JSONFormatter(
                service_name=service_name,
                version=version,
                environment=settings.environment,
                git_commit=build_info.short_commit,
            )
        )
    else:
        handler.setFormatter(TextFormatter(service_name=service_name))

    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # 抑制第三方库日志
    if suppress_third_party:
        for logger_name, logger_level in SUPPRESSED_LOGGERS.items():
            logging.getLogger(logger_name).setLevel(logger_level)


def get_logger(name: str) -> logging.Logger:
    """获取 logger

    Args:
        name: logger 名称，通常传入 __name__

    Returns:
        配置好的 logger
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """支持额外上下文的 Logger 适配器"""

    def process(
        self, msg: str, kwargs: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        # 将 extra 中的数据添加到 record
        extra = kwargs.get("extra", {})
        extra["extra_data"] = self.extra
        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(name: str, **context: Any) -> LoggerAdapter:
    """获取带上下文的 logger

    Args:
        name: logger 名称
        **context: 要绑定的上下文数据

    Returns:
        带上下文的 logger

    Example:
        ```python
        logger = get_context_logger(__name__, user_id="123", action="login")
        logger.info("User logged in")  # 自动包含 user_id 和 action
        ```
    """
    return LoggerAdapter(logging.getLogger(name), context)
