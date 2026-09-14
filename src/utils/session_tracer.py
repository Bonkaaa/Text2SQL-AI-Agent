"""Session Execution Tracer & Artifacts Logger.

Tiện ích lưu vết toàn bộ luồng thực thi và kết quả trung gian của các Subagents
vào thư mục outputs/{timestamp}_{session_id[:8]} phục vụ debug, kiểm thử và minh chứng đồ án.
Cơ chế Fail-Safe: mọi thao tác I/O ổ đĩa đều bọc an toàn, không bao giờ làm sập pipeline.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.config import get_settings

logger = logging.getLogger(__name__)


class SessionTracer:
    """Quản lý lưu vết thực thi (Execution Trace Artifacts) cho từng phiên truy vấn.

    Tự động tạo thư mục outputs/{timestamp}_{session_id[:8]} và lưu các artifact:
    - Text/SQL/Markdown (.sql, .md, .txt)
    - Structured JSON (.json) từ Dict, List, hoặc Pydantic BaseModel.
    """

    def __init__(
        self,
        session_id: str,
        base_dir: str | Path | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Khởi tạo SessionTracer cho một phiên truy vấn.

        Args:
            session_id: Định danh phiên truy vấn.
            base_dir: Đường dẫn thư mục gốc (mặc định lấy từ settings.trace_output_dir).
            enabled: Bật/tắt tính năng lưu trace (mặc định lấy từ settings.enable_trace_logging).
        """
        settings = get_settings()
        self.session_id = session_id
        self.enabled = enabled if enabled is not None else settings.enable_trace_logging
        self.base_dir = Path(base_dir or settings.trace_output_dir)

        self._trace_dir: Path | None = None
        if self.enabled:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")[:8]
            self._trace_dir = self.base_dir / f"{timestamp}_{safe_id}"
            try:
                self._trace_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning(
                    "Không thể tạo thư mục trace %s: %s. Hủy kích hoạt tracer cho phiên này.",
                    self._trace_dir,
                    exc,
                )
                self._trace_dir = None

    def get_trace_dir(self) -> Path | None:
        """Lấy đường dẫn thư mục trace của phiên hiện tại."""
        return self._trace_dir

    def log_artifact(self, filename: str, content: Any) -> Path | None:
        """Ghi một tệp artifact vào thư mục trace của phiên.

        Hỗ trợ tự động chuyển đổi:
        - Pydantic BaseModel -> JSON UTF-8
        - dict / list -> JSON UTF-8
        - str -> Text file UTF-8

        Args:
            filename: Tên tệp cần lưu (ví dụ: '02_schema_context.md', '03_draft_sql.sql').
            content: Nội dung cần lưu (str, dict, list hoặc BaseModel).

        Returns:
            Path của tệp đã lưu nếu thành công, hoặc None nếu thất bại / disabled.
        """
        if not self.enabled or self._trace_dir is None:
            return None

        try:
            file_path = self._trace_dir / filename

            # 1. Pydantic Model
            if isinstance(content, BaseModel):
                data_dict = content.model_dump(mode="json")
                json_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
                file_path.write_text(json_str, encoding="utf-8")

            # 2. Dict hoặc List
            elif isinstance(content, (dict, list)):
                json_str = json.dumps(
                    content, indent=2, ensure_ascii=False, default=str
                )
                file_path.write_text(json_str, encoding="utf-8")

            # 3. String hoặc các kiểu thô khác
            else:
                file_path.write_text(str(content), encoding="utf-8")

            logger.debug("Đã lưu artifact trace: %s", file_path)
            return file_path

        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            # Cơ chế Fail-Safe: không ném ngoại lệ làm gián đoạn luồng chính
            logger.warning("Lỗi khi ghi artifact trace %s: %s", filename, exc)
            return None

    def log_summary(
        self,
        status: str,
        total_time_ms: float = 0.0,
        retry_count: int = 0,
        question: str | None = None,
        error: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Path | None:
        """Ghi tệp metadata.json tóm tắt kết quả và chỉ số toàn bộ phiên chạy.

        Args:
            status: Trạng thái kết thúc ('SUCCESS', 'FAILED', 'BLOCKED'...).
            total_time_ms: Tổng thời gian thực thi (ms).
            retry_count: Số lần đã retry tự sửa lỗi.
            question: Câu hỏi gốc ban đầu.
            error: Thông báo lỗi nếu phiên thất bại.
            extra: Các thông số mở rộng tùy chọn khác.

        Returns:
            Path của file metadata.json đã lưu nếu thành công, hoặc None.
        """
        payload: dict[str, Any] = {
            "session_id": self.session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": status,
            "total_time_ms": total_time_ms,
            "retry_count": retry_count,
            "question": question,
            "error": error,
        }
        if extra:
            payload.update(extra)

        return self.log_artifact("metadata.json", payload)
