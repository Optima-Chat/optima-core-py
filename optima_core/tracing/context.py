"""追踪上下文模块"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

# 上下文变量
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_parent_span_id_var: ContextVar[Optional[str]] = ContextVar("parent_span_id", default=None)


@dataclass
class TraceContext:
    """追踪上下文数据"""

    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    parent_span_id: Optional[str] = None


def get_trace_id() -> Optional[str]:
    """获取当前追踪 ID"""
    return _trace_id_var.get()


def get_request_id() -> Optional[str]:
    """获取当前请求 ID"""
    return _request_id_var.get()


def get_parent_span_id() -> Optional[str]:
    """获取父级 Span ID"""
    return _parent_span_id_var.get()


def set_trace_context(
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
) -> None:
    """设置追踪上下文

    Args:
        trace_id: 追踪 ID
        request_id: 请求 ID
        parent_span_id: 父级 Span ID
    """
    if trace_id is not None:
        _trace_id_var.set(trace_id)
    if request_id is not None:
        _request_id_var.set(request_id)
    if parent_span_id is not None:
        _parent_span_id_var.set(parent_span_id)


def clear_trace_context() -> None:
    """清除追踪上下文"""
    _trace_id_var.set(None)
    _request_id_var.set(None)
    _parent_span_id_var.set(None)


def get_current_context() -> TraceContext:
    """获取当前完整追踪上下文"""
    return TraceContext(
        trace_id=get_trace_id(),
        request_id=get_request_id(),
        parent_span_id=get_parent_span_id(),
    )
