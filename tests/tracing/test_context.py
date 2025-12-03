"""追踪上下文测试"""

import asyncio

import pytest

from optima_core.tracing.context import (
    TraceContext,
    clear_trace_context,
    get_current_context,
    get_parent_span_id,
    get_request_id,
    get_trace_id,
    set_trace_context,
)


class TestTraceContext:
    """追踪上下文测试"""

    def setup_method(self) -> None:
        """每个测试前清理上下文"""
        clear_trace_context()

    def teardown_method(self) -> None:
        """每个测试后清理上下文"""
        clear_trace_context()

    def test_set_and_get(self) -> None:
        """测试设置和获取"""
        set_trace_context(
            trace_id="trace-123",
            request_id="req-456",
            parent_span_id="span-789",
        )

        assert get_trace_id() == "trace-123"
        assert get_request_id() == "req-456"
        assert get_parent_span_id() == "span-789"

    def test_partial_set(self) -> None:
        """测试部分设置"""
        set_trace_context(trace_id="trace-123")

        assert get_trace_id() == "trace-123"
        assert get_request_id() is None
        assert get_parent_span_id() is None

    def test_clear(self) -> None:
        """测试清除"""
        set_trace_context(
            trace_id="trace-123",
            request_id="req-456",
        )
        clear_trace_context()

        assert get_trace_id() is None
        assert get_request_id() is None

    def test_get_current_context(self) -> None:
        """测试获取完整上下文"""
        set_trace_context(
            trace_id="trace-123",
            request_id="req-456",
            parent_span_id="span-789",
        )

        ctx = get_current_context()

        assert isinstance(ctx, TraceContext)
        assert ctx.trace_id == "trace-123"
        assert ctx.request_id == "req-456"
        assert ctx.parent_span_id == "span-789"

    @pytest.mark.asyncio
    async def test_async_context_isolation(self) -> None:
        """测试异步上下文隔离"""
        results = []

        async def task(trace_id: str) -> None:
            set_trace_context(trace_id=trace_id)
            await asyncio.sleep(0.01)
            results.append(get_trace_id())

        await asyncio.gather(
            task("trace-1"),
            task("trace-2"),
            task("trace-3"),
        )

        # 每个任务应该有自己的上下文
        assert "trace-1" in results
        assert "trace-2" in results
        assert "trace-3" in results


class TestTraceContextDataclass:
    """TraceContext 数据类测试"""

    def test_default_values(self) -> None:
        """测试默认值"""
        ctx = TraceContext()

        assert ctx.trace_id is None
        assert ctx.request_id is None
        assert ctx.parent_span_id is None

    def test_with_values(self) -> None:
        """测试带值初始化"""
        ctx = TraceContext(
            trace_id="trace-123",
            request_id="req-456",
            parent_span_id="span-789",
        )

        assert ctx.trace_id == "trace-123"
        assert ctx.request_id == "req-456"
        assert ctx.parent_span_id == "span-789"
