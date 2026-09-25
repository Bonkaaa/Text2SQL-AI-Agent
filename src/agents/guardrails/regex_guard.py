"""Regex Guardrails Layer (Component 2.5.1 - Tier 1).

Đóng vai trò là chốt chặn an ninh đầu tiên (Deterministic Fast-Check) tại cổng đón tiếp:
- Tốc độ xử lý: < 0.1ms, chi phí: 0 token LLM.
- Chặn đứng 3 nhóm tấn công:
  1. DDL/DML Mutating SQL Injection (DROP, ALTER, TRUNCATE, DELETE, UPDATE, INSERT, batch injection, UNION, system probing).
  2. Prompt Injection & System Prompt Exfiltration (Jailbreak, DAN mode, ignore instructions, trích xuất system prompt).
  3. Script & Shell Injection (XSS, eval, exec, bash, cmd).
- Tự động gắn Hardcoded Refusal Messages tĩnh để từ chối dứt khoát, không cho LLM cơ hội sinh phản hồi tự do.
- Giảm thiểu tối đa False Positive trên các câu hỏi phân tích kinh doanh thông thường (ví dụ: "tỷ lệ drop", "cập nhật doanh thu").
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Final

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. ENUMS VÀ MODELS
# ==============================================================================


class RegexViolationType(str, Enum):
    """Phân loại vi phạm an ninh do Regex Guardrails phát hiện."""

    DDL_DML_INJECTION = "DDL_DML_INJECTION"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    SCRIPT_INJECTION = "SCRIPT_INJECTION"


class RegexGuardResult(BaseModel):
    """Kết quả kiểm tra từ lớp Regex Guardrails."""

    is_safe: bool = Field(
        description="True nếu không phát hiện mẫu độc hại nào; False nếu bị chặn an ninh"
    )
    violation_type: RegexViolationType | None = Field(
        default=None,
        description="Loại vi phạm an ninh nếu is_safe là False"
    )
    matched_pattern: str | None = Field(
        default=None,
        description="Đoạn văn bản hoặc regex pattern đã kích hoạt cảnh báo"
    )
    refusal_message: str | None = Field(
        default=None,
        description="Thông báo từ chối tĩnh chuẩn hóa gửi cho người dùng"
    )


# ==============================================================================
# 2. HARDCODED REFUSAL MESSAGES
# ==============================================================================

HARDCODED_REFUSAL_MESSAGES: Final[dict[RegexViolationType, str]] = {
    RegexViolationType.DDL_DML_INJECTION: (
        "Yêu cầu của bạn bị từ chối do chứa lệnh hoặc cú pháp can thiệp cấu trúc dữ liệu không hợp lệ. "
        "Hệ thống chỉ hỗ trợ truy vấn đọc dữ liệu (SELECT)."
    ),
    RegexViolationType.PROMPT_INJECTION: (
        "Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin và bảo mật chỉ dẫn hệ thống."
    ),
    RegexViolationType.SCRIPT_INJECTION: (
        "Yêu cầu của bạn bị từ chối do chứa mã lệnh hoặc đoạn script không an toàn."
    ),
}


# ==============================================================================
# 3. PRE-COMPILED REGEX PATTERNS (TIER 1 DETECTORS)
# ==============================================================================

# Nhóm 1: DDL / DML Mutating SQL Injection
_DDL_DML_PATTERNS: Final[list[re.Pattern[str]]] = [
    # DDL: DROP / TRUNCATE / ALTER / CREATE
    re.compile(r"\bdrop\s+(table|database|schema|view|index)\b", re.IGNORECASE),
    re.compile(r"\btruncate\s+(table\s+)?\w+\b", re.IGNORECASE),
    re.compile(r"\balter\s+table\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bcreate\s+(table|database|schema|view)\b", re.IGNORECASE),
    # DML: DELETE FROM / UPDATE ... SET / INSERT INTO
    re.compile(r"\bdelete\s+from\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bupdate\s+\w+\s+set\b", re.IGNORECASE),
    re.compile(r"\binsert\s+into\s+\w+\b", re.IGNORECASE),
    # Permissions & Privileges
    re.compile(r"\bgrant\s+.+\s+to\s+\w+\b", re.IGNORECASE),
    re.compile(r"\brevoke\s+.+\s+from\s+\w+\b", re.IGNORECASE),
    # Batch injection & Comment tricks
    re.compile(r";\s*--", re.IGNORECASE),
    re.compile(r";\s*(drop|delete|insert|update|alter|truncate|create)\b", re.IGNORECASE),
    # UNION injection
    re.compile(r"\bunion\s+(all\s+)?select\b", re.IGNORECASE),
    # System probing & backdoors
    re.compile(r"\binformation_schema\b", re.IGNORECASE),
    re.compile(r"\b(xp_cmdshell|pg_sleep|sleep\s*\()\b", re.IGNORECASE),
]

# Nhóm 2: Prompt Injection & System Prompt Exfiltration
_PROMPT_INJECTION_PATTERNS: Final[list[re.Pattern[str]]] = [
    # Override instructions (Tiếng Anh & Tiếng Việt)
    re.compile(r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\b(bỏ qua|quên|xóa)\s+(mọi\s+)?(hướng dẫn|chỉ dẫn|quy tắc|câu lệnh trước)\b", re.IGNORECASE),
    # System prompt exfiltration (Tiếng Anh & Tiếng Việt)
    re.compile(r"\b(what is your|reveal|show(\s+me)?|print|display)\s+(your\s+)?(system\s+)?(prompt|instructions)\b", re.IGNORECASE),
    re.compile(r"\b(cho tôi xem|hiển thị|in ra)\s+(hướng dẫn hệ thống|chỉ dẫn hệ thống|(system\s+)?prompt)\b", re.IGNORECASE),
    # Jailbreak personas
    re.compile(r"\b(dan\s+mode|jailbreak|developer\s+mode|evil\s+mode|do anything now)\b", re.IGNORECASE),
]

# Nhóm 3: Script & Shell Injection
_SCRIPT_INJECTION_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"<script[\s\S]*?>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\b(eval|exec)\s*\(", re.IGNORECASE),
    re.compile(r"\b(bash\s+-c|cmd\.exe|powershell\s+-c)\b", re.IGNORECASE),
]


# ==============================================================================
# 4. HÀM THỰC THI KIỂM SOÁT ĐẦU VÀO (ENTRYPOINT)
# ==============================================================================


def evaluate_regex_guardrails(question: str) -> RegexGuardResult:
    """Kiểm tra câu hỏi người dùng qua các biểu thức chính quy bảo vệ.

    Args:
        question: Chuỗi câu hỏi tự nhiên từ người dùng.

    Returns:
        RegexGuardResult chứa trạng thái is_safe, loại vi phạm và câu từ chối cứng nếu có.
    """
    cleaned_question = question.strip() if question else ""
    if not cleaned_question:
        return RegexGuardResult(is_safe=True)

    # 1. Kiểm tra DDL / DML Mutating SQL Injection
    for pattern in _DDL_DML_PATTERNS:
        match = pattern.search(cleaned_question)
        if match:
            matched_str = match.group(0)
            logger.warning(
                f"[RegexGuard] Phát hiện DDL/DML injection: '{matched_str}' trong câu hỏi: '{cleaned_question}'"
            )
            return RegexGuardResult(
                is_safe=False,
                violation_type=RegexViolationType.DDL_DML_INJECTION,
                matched_pattern=matched_str,
                refusal_message=HARDCODED_REFUSAL_MESSAGES[RegexViolationType.DDL_DML_INJECTION],
            )

    # 2. Kiểm tra Prompt Injection & Jailbreak
    for pattern in _PROMPT_INJECTION_PATTERNS:
        match = pattern.search(cleaned_question)
        if match:
            matched_str = match.group(0)
            logger.warning(
                f"[RegexGuard] Phát hiện Prompt Injection: '{matched_str}' trong câu hỏi: '{cleaned_question}'"
            )
            return RegexGuardResult(
                is_safe=False,
                violation_type=RegexViolationType.PROMPT_INJECTION,
                matched_pattern=matched_str,
                refusal_message=HARDCODED_REFUSAL_MESSAGES[RegexViolationType.PROMPT_INJECTION],
            )

    # 3. Kiểm tra Script / Shell Injection
    for pattern in _SCRIPT_INJECTION_PATTERNS:
        match = pattern.search(cleaned_question)
        if match:
            matched_str = match.group(0)
            logger.warning(
                f"[RegexGuard] Phát hiện Script Injection: '{matched_str}' trong câu hỏi: '{cleaned_question}'"
            )
            return RegexGuardResult(
                is_safe=False,
                violation_type=RegexViolationType.SCRIPT_INJECTION,
                matched_pattern=matched_str,
                refusal_message=HARDCODED_REFUSAL_MESSAGES[RegexViolationType.SCRIPT_INJECTION],
            )

    return RegexGuardResult(
        is_safe=True,
        violation_type=None,
        matched_pattern=None,
        refusal_message=None,
    )
