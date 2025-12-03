"""追踪 ID 生成测试"""

import time

from optima_core.tracing.ids import generate_request_id, generate_trace_id, parse_trace_id


class TestGenerateTraceId:
    """generate_trace_id 测试"""

    def test_format(self) -> None:
        """测试格式"""
        trace_id = generate_trace_id("auth")

        parts = trace_id.split("-")
        assert len(parts) == 3
        assert parts[2] == "auth"
        assert len(parts[1]) == 12  # random hex

    def test_unique(self) -> None:
        """测试唯一性"""
        ids = [generate_trace_id("svc") for _ in range(100)]
        assert len(set(ids)) == 100

    def test_timestamp_sortable(self) -> None:
        """测试时间戳可排序"""
        time.sleep(0.01)
        id1 = generate_trace_id("svc")
        time.sleep(0.01)
        id2 = generate_trace_id("svc")

        # 解析时间戳
        ts1 = int(id1.split("-")[0], 16)
        ts2 = int(id2.split("-")[0], 16)

        assert ts2 >= ts1

    def test_default_service_short(self) -> None:
        """测试默认服务简称"""
        trace_id = generate_trace_id()
        assert "-svc" in trace_id


class TestGenerateRequestId:
    """generate_request_id 测试"""

    def test_format(self) -> None:
        """测试格式"""
        request_id = generate_request_id("auth")

        assert request_id.startswith("auth_")
        assert len(request_id) == len("auth_") + 12

    def test_unique(self) -> None:
        """测试唯一性"""
        ids = [generate_request_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_default_prefix(self) -> None:
        """测试默认前缀"""
        request_id = generate_request_id()
        assert request_id.startswith("req_")


class TestParseTraceId:
    """parse_trace_id 测试"""

    def test_valid_trace_id(self) -> None:
        """测试解析有效 trace_id"""
        trace_id = generate_trace_id("auth")
        result = parse_trace_id(trace_id)

        assert result["valid"] is True
        assert result["service_short"] == "auth"
        assert isinstance(result["timestamp"], int)
        assert len(result["random"]) == 12

    def test_invalid_trace_id(self) -> None:
        """测试解析无效 trace_id"""
        result = parse_trace_id("invalid")

        assert result["valid"] is False
        assert result["raw"] == "invalid"

    def test_service_short_with_dash(self) -> None:
        """测试服务简称包含连字符"""
        trace_id = "67890abc-f1e2d3c4b5a6-my-service"
        result = parse_trace_id(trace_id)

        assert result["valid"] is True
        assert result["service_short"] == "my-service"
