"""测试配置和 fixtures"""

import os
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optima_core.config.settings import reset_settings


@pytest.fixture(autouse=True)
def reset_env() -> Generator[None, None, None]:
    """每个测试前后重置环境变量"""
    # 保存原始环境
    original_env = os.environ.copy()

    # 设置测试默认值
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    os.environ.setdefault("LOG_FORMAT", "text")

    # 重置配置单例
    reset_settings()

    yield

    # 恢复原始环境
    os.environ.clear()
    os.environ.update(original_env)
    reset_settings()


@pytest.fixture
def app() -> FastAPI:
    """创建测试用 FastAPI 应用"""
    return FastAPI(title="Test App")


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """创建测试客户端"""
    return TestClient(app)
