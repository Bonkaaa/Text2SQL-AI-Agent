"""Unit tests cho response_assembler.py (Single Source of Truth & Fallback layers)."""

from src.models.artifacts import (
    ChartArtifact,
    QueryArtifact,
    ResponsePackage,
    TableArtifact,
)
from src.utils.response_assembler import assemble_query_response


def test_assemble_with_response_package_single_source_of_truth():
    """Kiểm tra khi có ResponsePackage, assembler ưu tiên trích xuất từ package."""
    chart = ChartArtifact(
        chart_type="bar",
        title="Top 5 khách hàng",
        x_key="c_name",
        y_keys=["total_spent"],
        data=[{"c_name": "Alice", "total_spent": 1000}],
    )
    table = TableArtifact(
        title="Bảng chi tiết",
        columns=["c_name", "total_spent"],
        rows=[{"c_name": "Alice", "total_spent": 1000}],
    )
    pkg = ResponsePackage(
        session_id="test_sess_01",
        layout="stacked",
        direct_answer="Doanh thu cao nhất thuộc về Alice với 1000 USD.",
        detailed_insight=["Khách hàng tập trung ở phân khúc cao cấp."],
        artifacts=[chart, table],
        executed_queries=[{"sql": "SELECT c_name, total_spent FROM customer_summary"}],
    )

    result = {
        "status": "COMPLETED",
        "response_package": pkg,
        "final_answer": "Câu trả lời phụ",
    }

    resp = assemble_query_response(
        result=result,
        question="Ai là khách hàng chi tiêu nhiều nhất?",
        session_id="test_sess_01",
        elapsed_ms=120.5,
    )

    assert resp.status == "COMPLETED"
    assert resp.session_id == "test_sess_01"
    assert resp.final_answer == "Doanh thu cao nhất thuộc về Alice với 1000 USD."
    assert resp.sql == "SELECT c_name, total_spent FROM customer_summary"
    assert resp.data == [{"c_name": "Alice", "total_spent": 1000}]
    assert resp.columns == ["c_name", "total_spent"]
    assert resp.recharts_config is not None
    assert resp.recharts_config["chart_type"] == "bar"
    assert resp.recharts_config["x_key"] == "c_name"
    assert resp.response_package is not None
    assert len(resp.output_artifacts) == 2


def test_assemble_with_clarification_required():
    """Kiểm tra phản hồi ở trạng thái CLARIFICATION_REQUIRED."""
    result = {
        "status": "CLARIFICATION_REQUIRED",
        "is_ambiguous": True,
        "clarification_question": "Bạn muốn xem doanh thu theo năm 2002 hay 2003?",
        "suggested_options": ["Năm 2002", "Năm 2003"],
        "final_answer": "Vui lòng chọn năm cần phân tích.",
    }

    resp = assemble_query_response(
        result=result,
        question="Doanh thu bán hàng thế nào?",
        session_id="test_sess_02",
        elapsed_ms=45.0,
    )

    assert resp.status == "CLARIFICATION_REQUIRED"
    assert resp.is_ambiguous is True
    assert (
        resp.clarification_question == "Bạn muốn xem doanh thu theo năm 2002 hay 2003?"
    )
    assert resp.suggested_options == ["Năm 2002", "Năm 2003"]
    assert resp.sql is None
    assert resp.data is None


def test_assemble_with_security_blocked():
    """Kiểm tra phản hồi khi bị chặn an ninh (Hardcoded Refusal)."""
    result = {
        "status": "SECURITY_BLOCKED",
        "is_safe": False,
        "safety_category": "UNSAFE_PROMPT_INJECTION",
        "refusal_reason": "Yêu cầu bị từ chối do vi phạm chính sách an toàn thông tin.",
    }

    resp = assemble_query_response(
        result=result,
        question="DROP TABLE customer;",
        session_id="test_sess_03",
        elapsed_ms=10.0,
    )

    assert resp.status == "SECURITY_BLOCKED"
    assert resp.is_safe is False
    assert resp.safety_category == "UNSAFE_PROMPT_INJECTION"
    assert (
        resp.refusal_reason
        == "Yêu cầu bị từ chối do vi phạm chính sách an toàn thông tin."
    )
    assert (
        resp.final_answer
        == "Yêu cầu bị từ chối do vi phạm chính sách an toàn thông tin."
    )


def test_assemble_with_hitl_pending():
    """Kiểm tra phản hồi khi truy vấn yêu cầu phê duyệt HITL."""
    result = {
        "status": "PENDING_APPROVAL",
        "hitl_required": True,
        "sql": "SELECT * FROM store_sales",
        "estimated_cost_bytes": 10737418240,  # 10 GB
    }

    resp = assemble_query_response(
        result=result,
        question="Truy vấn toàn bộ store_sales",
        session_id="test_sess_04",
        elapsed_ms=50.0,
    )

    assert resp.status == "PENDING_APPROVAL"
    assert resp.requires_hitl is True
    assert resp.sql == "SELECT * FROM store_sales"
    assert resp.estimated_cost_bytes == 10737418240


def test_assemble_fallback_to_query_artifacts():
    """Kiểm tra fallback sang QueryArtifacts khi không có ResponsePackage."""
    q_art = QueryArtifact(
        task_id="task_1",
        description="Lấy doanh thu 2002",
        sql="SELECT year, sum(sales) FROM store_sales GROUP BY 1",
        data=[{"year": 2002, "sales": 50000}],
        columns=["year", "sales"],
        row_count=1,
        execution_time_ms=15.0,
        status="SUCCESS",
    )
    result = {
        "status": "COMPLETED",
        "artifacts": [q_art],
        "final_answer": "Doanh thu năm 2002 là 50,000 USD.",
    }

    resp = assemble_query_response(
        result=result,
        question="Doanh thu 2002?",
        session_id="test_sess_05",
        elapsed_ms=60.0,
    )

    assert resp.status == "COMPLETED"
    assert resp.sql == "SELECT year, sum(sales) FROM store_sales GROUP BY 1"
    assert resp.data == [{"year": 2002, "sales": 50000}]
    assert resp.columns == ["year", "sales"]
    assert resp.final_answer == "Doanh thu năm 2002 là 50,000 USD."
