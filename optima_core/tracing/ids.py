"""追踪 ID 生成模块"""

import secrets
import time


def generate_trace_id(service_short: str = "svc") -> str:
    """生成追踪 ID

    格式: {timestamp_hex}-{random_hex}-{service_short}
    示例: 67890abc-f1e2d3c4b5a6-auth

    Args:
        service_short: 服务简称（建议 3-5 字符）

    Returns:
        追踪 ID
    """
    timestamp_hex = format(int(time.time()), "x")
    random_hex = secrets.token_hex(6)  # 12 字符
    return f"{timestamp_hex}-{random_hex}-{service_short}"


def generate_request_id(prefix: str = "req") -> str:
    """生成请求 ID

    格式: {prefix}_{random_hex}
    示例: req_a1b2c3d4e5f6

    Args:
        prefix: ID 前缀

    Returns:
        请求 ID
    """
    random_hex = secrets.token_hex(6)  # 12 字符
    return f"{prefix}_{random_hex}"


def parse_trace_id(trace_id: str) -> dict:
    """解析追踪 ID

    Args:
        trace_id: 追踪 ID

    Returns:
        解析结果字典，包含 timestamp, random, service_short
    """
    try:
        parts = trace_id.split("-")
        if len(parts) >= 3:
            timestamp_hex = parts[0]
            random_hex = parts[1]
            service_short = "-".join(parts[2:])  # 处理 service_short 中可能有 -
            return {
                "timestamp": int(timestamp_hex, 16),
                "random": random_hex,
                "service_short": service_short,
                "valid": True,
            }
    except (ValueError, IndexError):
        pass

    return {"valid": False, "raw": trace_id}
