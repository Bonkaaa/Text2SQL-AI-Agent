"""Helper chuẩn hóa lắp ráp QueryResponse từ kết quả của Deep Agent Supervisor.

Tái sử dụng chung giữa FastAPI Gateway (/api/v1/query/ask) và CLI Runner (scripts/test_agent.py)
nhằm bảo đảm đồng nhất 100% Output Schema và lưu vết đầy đủ vào tệp trace `query_response.json`.
"""

import json
import re
from typing import Any

from src.agents.supervisor import extract_message_text
from src.models.api_schemas import QueryResponse
from src.models.rbac import UserContext


def assemble_query_response(
    result: dict[str, Any],
    question: str,
    session_id: str,
    elapsed_ms: float,
    user_context: UserContext | None = None,
    session_token: str | None = None,
) -> QueryResponse:
    """Lắp ráp kết quả của Deep Agent Supervisor thành schema QueryResponse chuẩn.

    Tự động trích xuất các trường:
    - sql (từ result, artifacts hoặc messages)
    - data & columns (từ result, artifacts hoặc messages)
    - recharts_config (từ visualization, artifacts hoặc JSON Markdown block)
    - response_package & output_artifacts (nếu có)
    - pre-flight safety & clarification
    """
    raw_status = str(result.get("status", "COMPLETED")).upper()
    status_str = raw_status

    final_answer = result.get("final_answer")
    if final_answer is not None:
        final_answer = extract_message_text(final_answer)

    messages = result.get("messages", [])
    if not final_answer and messages:
        final_answer = extract_message_text(
            getattr(messages[-1], "content", messages[-1])
        )

    sql = result.get("sql")
    data = result.get("data")
    columns = result.get("columns")
    recharts_config = result.get("visualization")
    response_package = result.get("response_package")
    output_artifacts = result.get("output_artifacts")
    artifacts = result.get("artifacts")

    # 1. ƯU TIÊN CAO NHẤT: Trích xuất trực tiếp từ ResponsePackage (Single Source of Truth)
    if response_package:
        pkg_obj = response_package
        if hasattr(pkg_obj, "model_dump"):
            pkg_artifacts = getattr(pkg_obj, "artifacts", [])
            pkg_queries = getattr(pkg_obj, "executed_queries", [])
            pkg_answer = getattr(pkg_obj, "direct_answer", None)
        elif isinstance(pkg_obj, dict):
            pkg_artifacts = pkg_obj.get("artifacts", [])
            pkg_queries = pkg_obj.get("executed_queries", [])
            pkg_answer = pkg_obj.get("direct_answer")
        else:
            pkg_artifacts, pkg_queries, pkg_answer = [], [], None

        if pkg_answer:
            final_answer = pkg_answer

        # Lấy SQL từ executed_queries trong package
        if not sql and pkg_queries and isinstance(pkg_queries, list):
            first_q = pkg_queries[0]
            sql = (
                first_q.get("sql")
                if isinstance(first_q, dict)
                else getattr(first_q, "sql", None)
            )

        # Lấy Chart / Table adapter từ artifacts trong package
        for item in pkg_artifacts:
            item_type = (
                item.get("type")
                if isinstance(item, dict)
                else getattr(item, "type", None)
            )
            if item_type == "chart" and not recharts_config:
                if isinstance(item, dict):
                    recharts_config = {
                        "chart_type": item.get("chart_type", "bar"),
                        "title": item.get("title"),
                        "x_key": item.get("x_key"),
                        "y_keys": item.get("y_keys", []),
                        "series_labels": item.get("series_labels", {}),
                    }
                else:
                    recharts_config = {
                        "chart_type": getattr(item, "chart_type", "bar"),
                        "title": getattr(item, "title", None),
                        "x_key": getattr(item, "x_key", None),
                        "y_keys": getattr(item, "y_keys", []),
                        "series_labels": getattr(item, "series_labels", {}),
                    }
            elif item_type == "table" and not data:
                if isinstance(item, dict):
                    data = item.get("rows")
                    columns = item.get("columns")
                else:
                    data = getattr(item, "rows", None)
                    columns = getattr(item, "columns", None)

    # 2. ƯU TIÊN THỨ HAI: Trích xuất từ QueryArtifacts list
    if artifacts and isinstance(artifacts, list):
        for art in artifacts:
            if not sql:
                sql = getattr(art, "sql", None) or (
                    art.get("sql") if isinstance(art, dict) else None
                )
            if not data:
                data = getattr(art, "data", None) or (
                    art.get("data") if isinstance(art, dict) else None
                )
            if not columns:
                columns = getattr(art, "columns", None) or (
                    art.get("columns") if isinstance(art, dict) else None
                )
            if sql and data:
                break

    # 3. FALLBACK CỐI CÙNG (Chỉ kích hoạt khi không có ResponsePackage và không có QueryArtifacts)
    if not recharts_config and final_answer:
        json_matches = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", final_answer)
        for jm in json_matches:
            try:
                pj = json.loads(jm)
                if isinstance(pj, dict):
                    if "recharts_config" in pj and isinstance(
                        pj["recharts_config"], dict
                    ):
                        recharts_config = pj["recharts_config"]
                        if "chart_type" in pj and "chart_type" not in recharts_config:
                            recharts_config["chart_type"] = pj["chart_type"]
                        break
                    elif "chart_type" in pj or "x_key" in pj:
                        recharts_config = pj
                        break
            except (json.JSONDecodeError, ValueError):
                continue

    if not sql and messages:
        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            sql_match = re.search(
                r"-\s*Câu lệnh đã chạy:\s*(SELECT[\s\S]+?)(?:\n-|\Z)",
                c_text,
                re.IGNORECASE,
            )
            if sql_match:
                sql = sql_match.group(1).strip()
                break
            sql_block = re.search(
                r"```sql\s*(SELECT[\s\S]+?)\s*```", c_text, re.IGNORECASE
            )
            if sql_block:
                sql = sql_block.group(1).strip()
                break

    if not data and messages:
        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            data_match = re.search(r"-\s*Dữ liệu mẫu thực tế:\s*(\[[\s\S]+?\])", c_text)
            if data_match:
                try:
                    parsed_sample = json.loads(data_match.group(1))
                    if isinstance(parsed_sample, list) and parsed_sample:
                        data = parsed_sample
                        if not columns and isinstance(data[0], dict):
                            columns = list(data[0].keys())
                    break
                except (json.JSONDecodeError, ValueError):
                    pass

    # 5. Kiểm tra trạng thái tạm dừng chờ duyệt HITL (PendingApprovalStore)
    from src.agents.control_pipeline.pending_store import get_pending_approval

    pending_app = get_pending_approval(session_id)
    requires_hitl = (
        (status_str == "PENDING_APPROVAL")
        or bool(result.get("hitl_required", False))
        or (pending_app is not None)
    )
    estimated_cost_bytes = result.get("estimated_cost_bytes")
    if pending_app:
        status_str = "PENDING_APPROVAL"
        if not estimated_cost_bytes:
            estimated_cost_bytes = pending_app.estimated_bytes
        if not sql:
            sql = pending_app.sql

    if not requires_hitl and messages:
        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            if (
                "BLOCKED_HITL" in c_text
                or "HITL Required" in c_text
                or "TẠM DỪNG CHỜ PHÊ DUYỆT" in c_text
            ):
                requires_hitl = True
                status_str = "PENDING_APPROVAL"
                cost_m = re.search(r"Dung lượng quét ước tính:\s*(\d+)", c_text)
                if cost_m:
                    estimated_cost_bytes = int(cost_m.group(1))
                sql_m = re.search(
                    r"-\s*Câu lệnh:\s*(SELECT[\s\S]+?)(?:\n-|\Z)", c_text, re.IGNORECASE
                )
                if sql_m and not sql:
                    sql = sql_m.group(1).strip()
                break

    # 6. Serialize ResponsePackage và AnalysisPlan tasks
    pkg_dump = None
    if response_package:
        if hasattr(response_package, "model_dump"):
            pkg_dump = response_package.model_dump()
        elif isinstance(response_package, dict):
            pkg_dump = response_package

    if not output_artifacts and pkg_dump and "artifacts" in pkg_dump:
        output_artifacts = pkg_dump["artifacts"]

    plan = result.get("plan")
    tasks_dump = None
    if plan and hasattr(plan, "tasks"):
        tasks_dump = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "status": t.status,
            }
            for t in plan.tasks
        ]
    elif result.get("tasks"):
        tasks_dump = result.get("tasks")

    # 7. An ninh và Hardcoded Refusal
    is_safe = result.get("is_safe", True)
    safety_category = result.get("safety_category")
    refusal_reason = result.get("refusal_reason")
    if status_str == "SECURITY_BLOCKED":
        is_safe = False
        if not final_answer:
            final_answer = refusal_reason

    # Đảm bảo status_str thuộc đúng enum Literal của QueryResponse
    allowed_statuses = {
        "COMPLETED",
        "SUCCESS",
        "CLARIFICATION_REQUIRED",
        "SECURITY_BLOCKED",
        "PENDING_APPROVAL",
        "ERROR",
    }
    if status_str not in allowed_statuses:
        status_str = (
            "ERROR" if "ERROR" in status_str or "FAILED" in status_str else "COMPLETED"
        )

    return QueryResponse(
        session_id=session_id,
        session_token=session_token,
        status=status_str,
        question=question,
        is_safe=is_safe,
        safety_category=safety_category,
        refusal_reason=refusal_reason,
        is_ambiguous=result.get("is_ambiguous", False),
        clarification_question=result.get("clarification_question"),
        suggested_options=result.get("suggested_options", []),
        final_answer=final_answer,
        sql=sql,
        data=data,
        columns=columns,
        recharts_config=recharts_config,
        intent=result.get("intent"),
        tasks=tasks_dump,
        artifacts=artifacts if artifacts else None,
        response_package=pkg_dump,
        output_artifacts=output_artifacts,
        insight=result.get("insight") or final_answer,
        visualization=result.get("visualization") or recharts_config,
        metadata={
            "query_count": len(artifacts) if isinstance(artifacts, list) else 0,
            "execution_time_ms": elapsed_ms,
        },
        requires_hitl=requires_hitl,
        estimated_cost_bytes=estimated_cost_bytes,
        execution_time_ms=elapsed_ms,
        error=result.get("error"),
    )
