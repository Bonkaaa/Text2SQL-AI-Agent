"""Quản lý bối cảnh phiên làm việc và chia sẻ dữ liệu phân tích giữa Deep Agent Supervisor và Subagents.

Sử dụng ContextVar chuẩn Python để bảo toàn session_id qua các coroutine asyncio,
đồng thời lưu trữ tạm thời ResponsePackage và Artifacts của subagent để Supervisor
có thể hợp nhất đầy đủ vào kết quả trả về cuối cùng.
"""

from __future__ import annotations

import contextvars
import threading
import time
from typing import Any

# ContextVar lưu session_id của request hiện tại
_current_session_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_session_id", default=""
)

# In-memory store lưu trữ kết quả phân tích theo session_id (thread-safe)
_lock = threading.Lock()
_analytics_store: dict[str, dict[str, Any]] = {}
_store_timestamps: dict[str, float] = {}
TTL_SECONDS = 3600  # 1 giờ


def set_current_session_id(session_id: str) -> contextvars.Token[str]:
    """Thiết lập session_id cho ngữ cảnh async hiện tại."""
    return _current_session_id.set(session_id)


def reset_current_session_id(token: contextvars.Token[str]) -> None:
    """Khôi phục session_id về trạng thái trước đó."""
    _current_session_id.reset(token)


def get_current_session_id() -> str:
    """Lấy session_id của ngữ cảnh hiện tại."""
    return _current_session_id.get()


def save_session_analytics(session_id: str, data: dict[str, Any]) -> None:
    """Lưu trữ kết quả phân tích (ResponsePackage, Artifacts, SQL,...) của subagent theo session_id."""
    if not session_id:
        return
    with _lock:
        _analytics_store[session_id] = data
        _store_timestamps[session_id] = time.time()
        _evict_expired()


def get_session_analytics(session_id: str) -> dict[str, Any] | None:
    """Lấy kết quả phân tích đã lưu theo session_id."""
    if not session_id:
        return None
    with _lock:
        return _analytics_store.get(session_id)


def clear_session_analytics(session_id: str) -> None:
    """Xóa dữ liệu phân tích của session_id sau khi đã tiêu thụ xong."""
    if not session_id:
        return
    with _lock:
        _analytics_store.pop(session_id, None)
        _store_timestamps.pop(session_id, None)


def _evict_expired() -> None:
    """Dọn dẹp các session đã quá hạn TTL (gọi bên trong lock)."""
    now = time.time()
    expired = [sid for sid, ts in _store_timestamps.items() if now - ts > TTL_SECONDS]
    for sid in expired:
        _analytics_store.pop(sid, None)
        _store_timestamps.pop(sid, None)
