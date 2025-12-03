"""
Optima Core - 服务核心库

提供可观测性、诊断端点、结构化日志、分布式追踪功能。
"""

from optima_core.diagnostics import (
    setup_health_routes,
    setup_debug_routes,
    run_startup_checks,
    HealthChecker,
    StartupChecker,
)
from optima_core.logging import configure_logging, get_logger
from optima_core.tracing import (
    TracingMiddleware,
    get_trace_id,
    get_request_id,
    set_trace_context,
    generate_trace_id,
    generate_request_id,
)
from optima_core.http import TracedHttpClient

__version__ = "0.1.0"

__all__ = [
    # Diagnostics
    "setup_health_routes",
    "setup_debug_routes",
    "run_startup_checks",
    "HealthChecker",
    "StartupChecker",
    # Logging
    "configure_logging",
    "get_logger",
    # Tracing
    "TracingMiddleware",
    "get_trace_id",
    "get_request_id",
    "set_trace_context",
    "generate_trace_id",
    "generate_request_id",
    # HTTP
    "TracedHttpClient",
]
