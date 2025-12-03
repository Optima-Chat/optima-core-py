"""日志配置测试"""

import json
import logging
import os
from io import StringIO

import pytest

from optima_core.logging import configure_logging, get_logger
from optima_core.tracing import set_trace_context, clear_trace_context


class TestConfigureLogging:
    """configure_logging 测试"""

    def test_basic_setup(self) -> None:
        """测试基本配置"""
        configure_logging(service_name="test-service", log_format="text")

        logger = get_logger(__name__)
        assert logger is not None

    def test_json_format(self, capfd: pytest.CaptureFixture[str]) -> None:
        """测试 JSON 格式日志"""
        os.environ["LOG_FORMAT"] = "json"
        configure_logging(service_name="test-service", log_format="json")

        logger = get_logger("test")
        logger.info("Test message")

        captured = capfd.readouterr()
        # 解析 JSON
        log_line = captured.out.strip()
        log_data = json.loads(log_line)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["service"] == "test-service"
        assert "timestamp" in log_data

    def test_text_format(self, capfd: pytest.CaptureFixture[str]) -> None:
        """测试文本格式日志"""
        configure_logging(service_name="test-service", log_format="text")

        logger = get_logger("test")
        logger.info("Test message")

        captured = capfd.readouterr()
        assert "test-service" in captured.out
        assert "Test message" in captured.out
        assert "[INFO]" in captured.out

    def test_json_includes_trace_id(self, capfd: pytest.CaptureFixture[str]) -> None:
        """测试 JSON 日志包含追踪 ID"""
        configure_logging(service_name="test-service", log_format="json")
        set_trace_context(trace_id="test-trace-123", request_id="req-456")

        try:
            logger = get_logger("test")
            logger.info("Test message")

            captured = capfd.readouterr()
            log_data = json.loads(captured.out.strip())

            assert log_data["trace_id"] == "test-trace-123"
            assert log_data["request_id"] == "req-456"
        finally:
            clear_trace_context()

    def test_text_includes_trace_id(self, capfd: pytest.CaptureFixture[str]) -> None:
        """测试文本日志包含追踪 ID"""
        configure_logging(service_name="test-service", log_format="text")
        set_trace_context(trace_id="test-trace-123")

        try:
            logger = get_logger("test")
            logger.info("Test message")

            captured = capfd.readouterr()
            assert "trace_id=test-trace-123" in captured.out
        finally:
            clear_trace_context()

    def test_log_level(self, capfd: pytest.CaptureFixture[str]) -> None:
        """测试日志级别配置"""
        configure_logging(
            service_name="test-service", log_level="WARNING", log_format="text"
        )

        logger = get_logger("test")
        logger.info("Info message")  # 不应输出
        logger.warning("Warning message")  # 应输出

        captured = capfd.readouterr()
        assert "Info message" not in captured.out
        assert "Warning message" in captured.out

    def test_json_exception(self, capfd: pytest.CaptureFixture[str]) -> None:
        """测试 JSON 日志包含异常信息"""
        configure_logging(service_name="test-service", log_format="json")

        logger = get_logger("test")
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Error occurred")

        captured = capfd.readouterr()
        log_data = json.loads(captured.out.strip())

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert "Test error" in log_data["exception"]["message"]
        assert "traceback" in log_data["exception"]

    def test_suppresses_third_party_loggers(self) -> None:
        """测试抑制第三方库日志"""
        configure_logging(
            service_name="test-service", log_format="text", suppress_third_party=True
        )

        httpx_logger = logging.getLogger("httpx")
        uvicorn_logger = logging.getLogger("uvicorn.access")

        assert httpx_logger.level == logging.WARNING
        assert uvicorn_logger.level == logging.WARNING


class TestGetLogger:
    """get_logger 测试"""

    def test_returns_logger(self) -> None:
        """测试返回 logger"""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_same_logger_instance(self) -> None:
        """测试返回相同 logger 实例"""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")
        assert logger1 is logger2
