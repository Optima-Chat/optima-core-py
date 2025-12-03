# optima-core-py

Optima 服务核心库：可观测性、诊断端点、结构化日志、分布式追踪。

## 功能

- **诊断端点**：增强的 `/health`、`/debug/info`、`/debug/config` 端点
- **结构化日志**：JSON 格式日志，支持 trace_id 关联
- **分布式追踪**：跨服务 trace_id 传递，支持蓝绿部署追踪
- **启动自检**：服务启动时检查依赖连接

## 安装

```bash
# 基础安装
pip install git+https://github.com/Optima-Yueliu/optima-core-py.git

# 包含 Redis 支持
pip install "optima-core[redis] @ git+https://github.com/Optima-Yueliu/optima-core-py.git"

# 包含 PostgreSQL 支持
pip install "optima-core[postgres] @ git+https://github.com/Optima-Yueliu/optima-core-py.git"

# 全部依赖
pip install "optima-core[all] @ git+https://github.com/Optima-Yueliu/optima-core-py.git"
```

## 快速开始

```python
import os
from fastapi import FastAPI
from optima_core import (
    configure_logging,
    setup_health_routes,
    setup_debug_routes,
    TracingMiddleware,
    run_startup_checks,
)

# 1. 配置日志
configure_logging(
    service_name="my-service",
    version=os.getenv("APP_VERSION", "0.1.0"),
)

# 2. 创建 FastAPI 应用
app = FastAPI()

# 3. 添加追踪中间件
app.add_middleware(TracingMiddleware, service_name="my-service")

# 4. 添加诊断路由
setup_health_routes(app, service_name="my-service")
setup_debug_routes(app)

# 5. 启动时自检（可选）
@app.on_event("startup")
async def startup():
    await run_startup_checks(
        service_name="my-service",
        checks={
            "database": check_database,
            "redis": check_redis,
        }
    )
```

## 端点说明

### GET /health

返回服务健康状态和版本信息：

```json
{
  "status": "healthy",
  "service": "my-service",
  "version": "0.1.0",
  "git_commit": "abc1234",
  "environment": "stage",
  "uptime_seconds": 3600,
  "timestamp": "2025-01-15T08:30:00Z",
  "checks": {
    "database": {"status": "healthy", "latency_ms": 5},
    "redis": {"status": "healthy", "latency_ms": 2}
  }
}
```

### GET /debug/info

返回构建和运行时信息：

```json
{
  "build": {
    "git_commit": "abc1234",
    "git_branch": "main",
    "build_date": "2025-01-15T08:00:00Z",
    "version": "0.1.0"
  },
  "runtime": {
    "python_version": "3.11.5",
    "environment": "stage",
    "log_level": "INFO"
  }
}
```

### GET /debug/config

需要 `X-Debug-Key` header，返回脱敏配置：

```bash
curl -H "X-Debug-Key: your-key" https://service/debug/config
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_VERSION` | `0.1.0` | 应用版本 |
| `GIT_COMMIT` | `unknown` | Git commit hash |
| `GIT_BRANCH` | `unknown` | Git 分支 |
| `BUILD_DATE` | `unknown` | 构建日期 |
| `ENVIRONMENT` | `development` | 运行环境 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `LOG_FORMAT` | `json` | 日志格式：json / text |
| `DEBUG_KEY` | (required) | /debug/config 访问密钥 |
| `DEPLOYMENT_ID` | - | 部署标识（蓝绿部署用） |

## 分布式追踪

### Header 规范

| Header | 说明 |
|--------|------|
| `X-Trace-ID` | 跨服务追踪 ID，入口服务生成 |
| `X-Request-ID` | 单次请求 ID，每个服务自己生成 |
| `X-Parent-Span-ID` | 父级 Span ID |
| `X-Deployment-ID` | 部署版本标识 |

### 服务间调用

使用 `TracedHttpClient` 自动传递追踪信息：

```python
from optima_core.http import TracedHttpClient

async with TracedHttpClient() as client:
    response = await client.get("http://other-service/api/data")
```

## 日志格式

JSON 格式（生产环境）：

```json
{
  "timestamp": "2025-01-15T08:30:00.123Z",
  "level": "INFO",
  "service": "my-service",
  "version": "0.1.0",
  "environment": "stage",
  "trace_id": "67890abc-f1e2d3c4b5a6-auth",
  "request_id": "req_abc123",
  "message": "Request completed"
}
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check .
mypy optima_core
```

## License

MIT
