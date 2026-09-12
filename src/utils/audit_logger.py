import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

AuditStatus = Literal[
    "SUCCESS",
    "BLOCKED_AST",
    "BLOCKED_RBAC",
    "BLOCKED_COST",
    "BLOCKED_HITL",
    "DB_ERROR",
    "TIMEOUT",
]


class AuditEvent(BaseModel):
    """Schema nhật ký kiểm toán (Audit Trail) ghi vết mọi truy vấn của người dùng."""

    query_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID duy nhất của lượt truy vấn (UUID v4)",
    )
    session_id: str = Field(description="ID phiên làm việc (thread_id)")
    user_id: str = Field(description="ID người dùng gửi yêu cầu")
    role: str = Field(description="Vai trò người dùng (Analyst / Admin)")
    question: str = Field(description="Câu hỏi ngôn ngữ tự nhiên ban đầu")
    sql: str = Field(description="Câu lệnh SQL được tạo ra hoặc bị chặn")
    status: AuditStatus = Field(description="Trạng thái kết quả kiểm duyệt/thực thi")
    bytes_scanned: int = Field(
        default=0, description="Dung lượng dữ liệu quét ước tính hoặc thực tế (bytes)"
    )
    execution_time_ms: float = Field(
        default=0.0, description="Thời gian thực thi truy vấn (mili-giây)"
    )
    error_message: str | None = Field(
        default=None, description="Chi tiết lỗi nếu truy vấn bị chặn hoặc thất bại"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Thời điểm ghi nhận sự kiện (UTC)",
    )


class AuditLogger:
    """Quản lý ghi và truy xuất nhật ký kiểm toán dưới dạng JSON Lines (JSONL)."""

    def __init__(self, log_file_path: str = "./data/logs/audit.jsonl") -> None:
        self.log_file_path = Path(log_file_path)

    def log_event(self, event: AuditEvent) -> bool:
        """Ghi sự kiện kiểm toán vào file JSONL với cơ chế Fail-Safe (không làm sập luồng chính).

        Args:
            event: Đối tượng sự kiện kiểm toán cần lưu.

        Returns:
            bool: True nếu ghi thành công, False nếu gặp lỗi I/O.
        """
        try:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            log_line = event.model_dump_json()

            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
            return True
        except (OSError, ValueError, TypeError) as exc:
            # Ghi nhận lỗi vào hệ thống log chuẩn nhưng không ném exception làm crash ứng dụng
            logger.error("Thất bại khi ghi audit log (Fail-Safe activated): %s", exc)
            return False

    def get_logs(
        self,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Đọc danh sách các sự kiện kiểm toán đã lưu, hỗ trợ lọc theo session_id.

        Args:
            session_id: ID phiên làm việc cần lọc (None để lấy tất cả).
            limit: Số lượng bản ghi tối đa trả về.

        Returns:
            list[AuditEvent]: Danh sách các sự kiện kiểm toán.
        """
        if not self.log_file_path.exists():
            return []

        events: list[AuditEvent] = []
        try:
            with open(self.log_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        event = AuditEvent.model_validate_json(stripped)
                        if session_id is None or event.session_id == session_id:
                            events.append(event)
                    except json.JSONDecodeError, ValueError:
                        continue
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Không thể đọc file audit log: %s", exc)
            return []

        # Trả về các sự kiện theo thứ tự giới hạn limit
        return events[:limit]


_default_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Singleton getter cho AuditLogger."""
    global _default_audit_logger
    if _default_audit_logger is None:
        _default_audit_logger = AuditLogger()
    return _default_audit_logger


def log_audit_event(event: AuditEvent) -> bool:
    """Hàm tiện ích cấp module ghi nhận sự kiện kiểm toán an toàn (Fail-Safe)."""
    return get_audit_logger().log_event(event)
