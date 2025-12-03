"""诊断模块：健康检查、调试端点、启动自检"""

from optima_core.diagnostics.health import (
    HealthChecker,
    setup_health_routes,
    create_health_check_database,
    create_health_check_redis,
    create_health_check_http,
)
from optima_core.diagnostics.endpoints import setup_debug_routes
from optima_core.diagnostics.startup import StartupChecker, run_startup_checks

__all__ = [
    "HealthChecker",
    "setup_health_routes",
    "create_health_check_database",
    "create_health_check_redis",
    "create_health_check_http",
    "setup_debug_routes",
    "StartupChecker",
    "run_startup_checks",
]
