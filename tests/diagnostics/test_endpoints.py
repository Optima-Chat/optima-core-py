"""调试端点测试"""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optima_core.diagnostics import setup_debug_routes


class TestDebugEndpoints:
    """调试端点测试"""

    def test_debug_info_without_key(self, app: FastAPI) -> None:
        """测试 /debug/info 不需要密钥"""
        setup_debug_routes(app)
        client = TestClient(app)

        response = client.get("/debug/info")

        assert response.status_code == 200
        data = response.json()
        assert "build" in data
        assert "runtime" in data
        assert "dependencies" in data

    def test_debug_info_with_require_key(self, app: FastAPI) -> None:
        """测试 /debug/info 需要密钥时"""
        os.environ["DEBUG_KEY"] = "test-key"
        setup_debug_routes(app, require_key_for_info=True)
        client = TestClient(app)

        # 无密钥
        response = client.get("/debug/info")
        assert response.status_code == 403

        # 错误密钥
        response = client.get("/debug/info", headers={"X-Debug-Key": "wrong"})
        assert response.status_code == 403

        # 正确密钥
        response = client.get("/debug/info", headers={"X-Debug-Key": "test-key"})
        assert response.status_code == 200

    def test_debug_config_requires_key(self, app: FastAPI) -> None:
        """测试 /debug/config 需要密钥"""
        setup_debug_routes(app)
        client = TestClient(app)

        # 未配置 DEBUG_KEY
        response = client.get("/debug/config")
        assert response.status_code == 503

    def test_debug_config_with_key(self, app: FastAPI) -> None:
        """测试 /debug/config 带正确密钥"""
        os.environ["DEBUG_KEY"] = "test-key"
        os.environ["DATABASE_URL"] = "postgresql://user:password@host/db"
        os.environ["APP_ENV"] = "test"

        setup_debug_routes(app)
        client = TestClient(app)

        response = client.get("/debug/config", headers={"X-Debug-Key": "test-key"})

        assert response.status_code == 200
        data = response.json()
        assert "config" in data

        # 验证 URL 密码被脱敏
        db_url = data["config"].get("DATABASE_URL", "")
        assert "password" not in db_url
        assert "***" in db_url

    def test_debug_config_masks_sensitive(self, app: FastAPI) -> None:
        """测试敏感信息脱敏"""
        os.environ["DEBUG_KEY"] = "test-key"
        os.environ["APP_SECRET_KEY"] = "super-secret-value"
        os.environ["APP_TOKEN"] = "token123"
        os.environ["APP_NORMAL"] = "normal-value"

        setup_debug_routes(app)
        client = TestClient(app)

        response = client.get("/debug/config", headers={"X-Debug-Key": "test-key"})

        assert response.status_code == 200
        data = response.json()

        # SECRET 和 TOKEN 应该被脱敏
        secret = data["config"].get("APP_SECRET_KEY", "")
        assert "super-secret-value" not in secret
        assert "chars" in secret

        token = data["config"].get("APP_TOKEN", "")
        assert "token123" not in token
        assert "chars" in token

    def test_debug_info_contains_versions(self, app: FastAPI) -> None:
        """测试 /debug/info 包含版本信息"""
        os.environ["GIT_COMMIT"] = "abc123def456"
        os.environ["GIT_BRANCH"] = "main"
        os.environ["APP_VERSION"] = "1.0.0"

        setup_debug_routes(app)
        client = TestClient(app)

        response = client.get("/debug/info")

        assert response.status_code == 200
        data = response.json()

        assert data["build"]["git_commit"] == "abc123def456"
        assert data["build"]["git_branch"] == "main"
        assert data["build"]["version"] == "1.0.0"

    def test_debug_info_contains_runtime(self, app: FastAPI) -> None:
        """测试 /debug/info 包含运行时信息"""
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["LOG_LEVEL"] = "DEBUG"

        setup_debug_routes(app)
        client = TestClient(app)

        response = client.get("/debug/info")

        assert response.status_code == 200
        data = response.json()

        assert data["runtime"]["environment"] == "staging"
        assert data["runtime"]["log_level"] == "DEBUG"
        assert "python_version" in data["runtime"]
