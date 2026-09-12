import json
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import ERROR_DIAGNOSTIC_PROMPT
from src.models.state import ControlState, DiagnosticResult
from src.services import get_chat_model

logger = logging.getLogger(__name__)


def get_diagnostic_llm() -> BaseChatModel | None:
    """Lấy Chat Model Tier 2 cho Diagnostic Agent từ LLM Service tập trung."""
    return get_chat_model(tier="tier2")


def map_error_type_to_category(
    error_type: str,
) -> str:
    """Ánh xạ error_type kỹ thuật sang error_category chuẩn của DiagnosticResult."""
    mapping = {
        "UNAUTHORIZED_COLUMN": "RBAC_VIOLATION",
        "UNAUTHORIZED_TABLE": "RBAC_VIOLATION",
        "FORBIDDEN_STATEMENT": "AST_VIOLATION",
        "MULTIPLE_STATEMENTS": "AST_VIOLATION",
        "SYNTAX_ERROR": "AST_VIOLATION",
        "EXCEEDED_COST_LIMIT": "COST_EXCEEDED",
        "TIMEOUT": "TIMEOUT",
        "HITL_REJECTED": "HITL_REJECTED",
        "RUNTIME_ERROR": "DB_RUNTIME_ERROR",
        "DB_ERROR": "DB_RUNTIME_ERROR",
    }
    return mapping.get(error_type, "UNKNOWN_ERROR")


def generate_rule_based_fallback(
    error_type: str,
    error_message: str,
) -> DiagnosticResult:
    """Tạo đối tượng DiagnosticResult dự phòng (Rule-based Fallback) khi không có LLM."""
    category = map_error_type_to_category(error_type)

    if error_type == "UNAUTHORIZED_COLUMN":
        offending = None
        for col in ["c_phone", "c_acctbal", "s_phone", "s_acctbal"]:
            if col in error_message:
                offending = col
                break
        feedback = (
            f"Truy vấn vi phạm chính sách bảo mật dữ liệu RBAC ({error_message}). "
            "Hãy loại bỏ các cột nhạy cảm bị cấm (như c_phone, c_acctbal, s_phone, s_acctbal) "
            "và thay bằng các cột định danh chung (như c_name, c_custkey)."
        )
        return DiagnosticResult(
            error_category="RBAC_VIOLATION",
            root_cause=f"Truy vấn vi phạm chính sách RBAC bảo vệ dữ liệu PII và tài chính: {error_message}",
            offending_entity=offending,
            suggested_fix="Loại bỏ các cột nhạy cảm khỏi SELECT/WHERE và thay bằng cột định danh không nhạy cảm (c_name, c_custkey).",
            actionable_feedback=feedback,
        )
    elif error_type == "UNAUTHORIZED_TABLE":
        feedback = (
            f"Truy vấn vi phạm quyền truy cập bảng ({error_message}). "
            "Người dùng chỉ được phép truy vấn 8 bảng nghiệp vụ TPC-H "
            "(customer, orders, lineitem, part, partsupp, supplier, nation, region)."
        )
        return DiagnosticResult(
            error_category="RBAC_VIOLATION",
            root_cause=f"Truy vấn truy cập bảng ngoài phạm vi quyền hạn được cấp: {error_message}",
            offending_entity=None,
            suggested_fix="Chỉ sử dụng 8 bảng TPC-H hợp lệ: customer, orders, lineitem, part, partsupp, supplier, nation, region.",
            actionable_feedback=feedback,
        )
    elif error_type == "FORBIDDEN_STATEMENT":
        feedback = (
            "Chỉ cho phép thực thi truy vấn đọc dữ liệu (SELECT). "
            "Tuyệt đối không sử dụng các câu lệnh DDL/DML thay đổi cấu trúc hoặc dữ liệu "
            "(DROP, DELETE, UPDATE, INSERT, ALTER)."
        )
        return DiagnosticResult(
            error_category="AST_VIOLATION",
            root_cause="Phát hiện câu lệnh SQL DDL/DML thay đổi dữ liệu hoặc cấu trúc bảng.",
            offending_entity="DDL/DML",
            suggested_fix="Loại bỏ các câu lệnh ngoài SELECT, chuyển đổi câu truy vấn về duy nhất một câu lệnh SELECT đọc dữ liệu.",
            actionable_feedback=feedback,
        )
    elif error_type == "EXCEEDED_COST_LIMIT":
        feedback = (
            "Dung lượng quét dữ liệu ước tính vượt quá ngân sách cho phép. "
            "Hãy bổ sung mệnh đề lọc WHERE (ví dụ lọc theo năm hoặc ngày tháng o_orderdate) "
            "và thêm mệnh đề LIMIT để giới hạn số dòng quét."
        )
        return DiagnosticResult(
            error_category="COST_EXCEEDED",
            root_cause="Ước lượng dung lượng quét dữ liệu bytes_scanned vượt quá hạn mức ngân sách cho phép của vai trò người dùng.",
            offending_entity=None,
            suggested_fix="Bổ sung điều kiện lọc thời gian cụ thể trong WHERE và bổ sung mệnh đề LIMIT để giảm dung lượng quét.",
            actionable_feedback=feedback,
        )
    elif error_type == "TIMEOUT":
        feedback = (
            "Truy vấn bị ngắt do vượt quá thời gian thực thi tối đa. "
            "Hãy tối ưu lại điều kiện JOIN giữa các bảng lớn (orders, lineitem) "
            "và thêm bộ lọc điều kiện WHERE để giảm tải cho engine."
        )
        return DiagnosticResult(
            error_category="TIMEOUT",
            root_cause="Thời gian thực thi truy vấn vượt quá giới hạn query_timeout_seconds (30s).",
            offending_entity=None,
            suggested_fix="Tối ưu lại các mệnh đề JOIN, tạo điều kiện lọc WHERE sớm trên bảng lớn và thêm LIMIT.",
            actionable_feedback=feedback,
        )
    elif error_type == "MULTIPLE_STATEMENTS":
        feedback = "Chỉ cho phép một câu lệnh SQL duy nhất. Hãy loại bỏ các câu lệnh nối tiếp sau dấu chấm phẩy."
        return DiagnosticResult(
            error_category="AST_VIOLATION",
            root_cause="Phát hiện nhiều câu lệnh SQL nối tiếp nhau bằng dấu chấm phẩy (nguy cơ SQL Injection).",
            offending_entity="MULTIPLE_STATEMENTS",
            suggested_fix="Tách riêng và chỉ giữ lại một câu lệnh SELECT duy nhất cần thực thi.",
            actionable_feedback=feedback,
        )
    elif error_type == "HITL_REJECTED":
        feedback = "Truy vấn đã bị từ chối bởi người dùng qua bước phê duyệt HITL. Hãy xem xét và viết lại câu lệnh phù hợp hơn."
        return DiagnosticResult(
            error_category="HITL_REJECTED",
            root_cause="Người dùng chủ động từ chối phê duyệt câu lệnh SQL trong cổng kiểm soát Human-In-The-Loop.",
            offending_entity=None,
            suggested_fix="Rà soát lại yêu cầu nghiệp vụ và điều chỉnh câu lệnh SQL trước khi gửi lại phê duyệt.",
            actionable_feedback=feedback,
        )

    feedback = (
        f"Phát hiện lỗi kỹ thuật: {error_message}. "
        "Hãy kiểm tra lại tính chính xác của tên cột, tên bảng và cú pháp SQL theo chuẩn dialect DuckDB."
    )
    return DiagnosticResult(
        error_category=category if category != "UNKNOWN_ERROR" else "DB_RUNTIME_ERROR",  # type: ignore[arg-type]
        root_cause=f"Lỗi cú pháp hoặc runtime từ database engine: {error_message}",
        offending_entity=None,
        suggested_fix="Kiểm tra lại schema context, sửa đúng tên cột/bảng và khớp cú pháp SQL theo chuẩn DuckDB.",
        actionable_feedback=feedback,
    )


def error_diagnostic_node(
    state: ControlState,
    llm: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Node Agentic: ERROR_DIAGNOSTIC_AGENT phân tích lỗi & tạo DiagnosticResult có cấu trúc.

    Nhận diện câu SQL lỗi, đối chiếu với Schema context và loại lỗi để sinh chỉ dẫn
    sửa lỗi cụ thể (DiagnosticResult) cho SQL Generator ở chu kỳ retry tiếp theo.
    """
    sql = state.get("sql", "")
    schema_context = state.get("schema_context", "")
    execution_result = state.get("execution_result") or {}

    error_type = execution_result.get("error_type") or state.get(
        "error_type", "UNKNOWN_ERROR"
    )
    error_message = execution_result.get("error_message") or state.get(
        "error_message", ""
    )

    active_llm = llm or get_diagnostic_llm()
    diag_result: DiagnosticResult | None = None

    if active_llm is not None:
        try:
            prompt_messages = ERROR_DIAGNOSTIC_PROMPT.format_messages(
                sql=sql,
                error_type=error_type,
                error_message=error_message or "Không có chi tiết lỗi.",
                schema_context=schema_context or "Không có ngữ cảnh schema bổ sung.",
            )

            # Ưu tiên sử dụng with_structured_output nếu mô hình hỗ trợ
            if hasattr(active_llm, "with_structured_output"):
                structured_llm = active_llm.with_structured_output(DiagnosticResult)
                response = structured_llm.invoke(prompt_messages)
                if isinstance(response, DiagnosticResult):
                    diag_result = response
                elif isinstance(response, dict):
                    diag_result = DiagnosticResult.model_validate(response)
            else:
                # LLM trực tiếp (mock hoặc custom runner)
                response = active_llm.invoke(prompt_messages)
                if isinstance(response, DiagnosticResult):
                    diag_result = response
                elif isinstance(response, dict):
                    diag_result = DiagnosticResult.model_validate(response)
                elif hasattr(response, "content") and response.content:
                    content = str(response.content).strip()
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            diag_result = DiagnosticResult.model_validate(data)
                    except Exception:  # noqa: BLE001
                        # Nếu LLM trả về text thông thường -> chuyển thành DiagnosticResult
                        diag_result = DiagnosticResult(
                            error_category=map_error_type_to_category(error_type),  # type: ignore[arg-type]
                            root_cause=error_message or "Lỗi truy vấn SQL",
                            offending_entity=None,
                            suggested_fix="Kiểm tra lại câu SQL theo chỉ dẫn.",
                            actionable_feedback=content,
                        )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Lỗi khi gọi Diagnostic LLM: %s. Kích hoạt Rule-based Fallback.", exc
            )
            diag_result = None

    # Nếu LLM không khả dụng hoặc gọi thất bại -> dùng Fallback
    if diag_result is None:
        diag_result = generate_rule_based_fallback(
            error_type=error_type, error_message=error_message
        )

    # Cập nhật kết quả vào execution_result và state
    updated_execution_result = dict(execution_result)
    updated_execution_result["diagnostic_result"] = diag_result
    updated_execution_result["actionable_feedback"] = diag_result.actionable_feedback

    return {
        "diagnostic_result": diag_result,
        "actionable_feedback": diag_result.actionable_feedback,
        "execution_result": updated_execution_result,
    }
