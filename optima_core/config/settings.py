"""全局设置"""

import os
from dataclasses import dataclass
from typing import Optional

_settings: Optional["Settings"] = None


@dataclass
class Settings:
    """全局配置"""

    # 环境
    environment: str
    debug: bool

    # 日志
    log_level: str
    log_format: str

    # 调试
    debug_key: Optional[str]

    # 部署
    deployment_id: Optional[str]

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量读取配置"""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("LOG_FORMAT", "json").lower(),
            debug_key=os.getenv("DEBUG_KEY"),
            deployment_id=os.getenv("DEPLOYMENT_ID"),
        )


def get_settings() -> Settings:
    """获取全局配置（单例）"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """重置配置（用于测试）"""
    global _settings
    _settings = None
