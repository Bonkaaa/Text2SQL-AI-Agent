"""Unit tests cho các Typed Artifact Contracts (Phase 1).

Kiểm tra:
- Tạo và xác thực QueryArtifact (cả thành công và lỗi).
- Tạo và xác thực AnalysisPlan và AnalysisTask.
- Đóng gói và tuần tự hóa ArtifactBundle.
- Khả năng tương thích giữa QueryArtifact và các models cũ.
"""

from src.models.artifacts import (
    AnalysisPlan,
    AnalysisTask,
    ArtifactBundle,
    ChartSpec,
    EvidenceStore,
    QueryArtifact,
    TableSpec,
)


def test_query_artifact_creation_success():
    """Kiểm tra khởi tạo QueryArtifact thành công với đầy đủ metadata."""
    artifact = QueryArtifact(
        task_id="task_1",
        sql="SELECT n_name, count(*) FROM customer JOIN nation ON c_nationkey = n_nationkey GROUP BY 1",
        dialect="duckdb",
        explanation="Thống kê số lượng khách hàng theo quốc gia",
        tables_used=["customer", "nation"],
        columns_used=["c_nationkey", "n_name", "n_nationkey"],
        status="SUCCESS",
        data=[{"n_name": "VIETNAM", "count": 120}],
        columns=["n_name", "count"],
        row_count=1,
        execution_time_ms=45.2,
    )

    assert artifact.artifact_id is not None
    assert artifact.task_id == "task_1"
    assert artifact.status == "SUCCESS"
    assert len(artifact.tables_used) == 2
    assert artifact.row_count == 1
    assert artifact.error_message is None

    # Kiểm tra serialization sang dict
    dump = artifact.model_dump()
    assert dump["status"] == "SUCCESS"
    assert dump["sql"].startswith("SELECT")


def test_query_artifact_creation_failure():
    """Kiểm tra khởi tạo QueryArtifact khi truy vấn bị lỗi hoặc bị chặn bởi Guardrails."""
    artifact = QueryArtifact(
        task_id="task_2",
        sql="DROP TABLE customer",
        status="BLOCKED_AST",
        error_message="Truy vấn DDL/DML bị từ chối bởi AST Sanitizer",
        execution_time_ms=1.5,
    )

    assert artifact.status == "BLOCKED_AST"
    assert artifact.row_count == 0
    assert artifact.data == []
    assert "AST Sanitizer" in artifact.error_message


def test_analysis_plan_and_evidence_store():
    """Kiểm tra luồng tạo kế hoạch AnalysisPlan và lưu trữ bằng chứng vào EvidenceStore."""
    task1 = AnalysisTask(
        task_id="t1",
        description="Tính tổng doanh thu theo quý trong năm 1995",
        status="COMPLETED",
    )
    task2 = AnalysisTask(
        task_id="t2",
        description="Phân tích top 5 nhà cung cấp đóng góp doanh thu lớn nhất",
        status="PLANNED",
    )

    plan = AnalysisPlan(
        goal="Đánh giá hiệu quả kinh doanh năm 1995",
        hypotheses=["Doanh thu quý 4 tăng trưởng vượt bậc"],
        tasks=[task1, task2],
        max_tasks=3,
    )

    assert len(plan.tasks) == 2
    assert plan.current_task.task_id == "t1"
    assert not plan.is_completed

    # Tạo artifact và lưu vào EvidenceStore
    art1 = QueryArtifact(
        task_id="t1",
        sql="SELECT sum(revenue) FROM orders",
        status="SUCCESS",
        data=[{"sum": 1000000}],
        row_count=1,
    )

    store = EvidenceStore(
        evidences=[art1],
        accumulated_findings=["Doanh thu năm 1995 đạt 1 triệu USD"],
    )

    assert len(store.evidences) == 1
    assert store.evidences[0].task_id == "t1"
    assert len(store.accumulated_findings) == 1


def test_artifact_bundle_serialization():
    """Kiểm tra đóng gói toàn bộ phiên phân tích vào ArtifactBundle."""
    chart = ChartSpec(
        chart_type="bar",
        title="Doanh thu theo vùng",
        x_axis_key="region",
        y_axis_keys=["revenue"],
        series_labels={"revenue": "Doanh thu (USD)"},
    )

    table = TableSpec(
        title="Chi tiết doanh thu",
        columns=["region", "revenue"],
        rows=[{"region": "ASIA", "revenue": 500000}],
    )

    artifact = QueryArtifact(
        task_id="t1",
        sql="SELECT r_name, sum(revenue) FROM ...",
        status="SUCCESS",
        row_count=1,
    )

    bundle = ArtifactBundle(
        session_id="test_session_123",
        analysis_goal="Phân tích thị trường",
        executive_summary="Thị trường ASIA dẫn đầu doanh số.",
        key_findings=["Doanh thu ASIA chiếm 50% tổng số."],
        recommended_actions=["Đẩy mạnh tiếp thị tại khu vực lân cận."],
        charts=[chart],
        tables=[table],
        executed_artifacts=[artifact],
        total_execution_time_ms=120.5,
    )

    dump = bundle.model_dump()
    assert dump["session_id"] == "test_session_123"
    assert len(dump["charts"]) == 1
    assert dump["charts"][0]["chart_type"] == "bar"
    assert len(dump["tables"]) == 1
    assert len(dump["executed_artifacts"]) == 1


def test_control_pipeline_execute_node_produces_artifact():
    """Kiểm tra execute_node trong Control Pipeline có sinh query_artifact hợp lệ."""
    from src.agents.control_pipeline.nodes import execute_node
    from src.models.rbac import UserContext, UserRole
    from src.models.state import ControlState

    state: ControlState = {
        "sql": "SELECT 1 as val",
        "session_id": "test_session",
        "user_context": UserContext(
            user_id="user1",
            role=UserRole.ANALYST,
            session_id="test_session",
        ),
        "is_valid": True,
        "ast_valid": True,
        "rbac_valid": True,
        "cost_valid": True,
        "hitl_required": False,
        "data": None,
        "columns": None,
        "query_artifact": None,
    }

    result = execute_node(state)

    assert result["is_valid"] is True
    assert "query_artifact" in result
    artifact: QueryArtifact = result["query_artifact"]
    assert isinstance(artifact, QueryArtifact)
    assert artifact.sql == "SELECT 1 as val"
    assert artifact.status == "SUCCESS"
    assert artifact.row_count == 1
    assert artifact.data == [{"val": 1}]


def test_control_pipeline_err_node_produces_artifact():
    """Kiểm tra err_node trong Control Pipeline có sinh query_artifact với status lỗi tương ứng."""
    from src.agents.control_pipeline.nodes import err_node
    from src.models.rbac import UserContext, UserRole
    from src.models.state import ControlState

    state: ControlState = {
        "sql": "DELETE FROM orders",
        "session_id": "test_err_session",
        "user_context": UserContext(
            user_id="user1",
            role=UserRole.ANALYST,
            session_id="test_err_session",
        ),
        "is_valid": False,
        "ast_valid": False,
        "error_type": "AST_SECURITY_VIOLATION",
        "error_message": "Chỉ cho phép truy vấn SELECT",
        "actionable_feedback": "Vui lòng chỉ sử dụng SELECT",
        "query_artifact": None,
    }

    result = err_node(state)

    assert result["is_valid"] is False
    assert "query_artifact" in result
    artifact: QueryArtifact = result["query_artifact"]
    assert isinstance(artifact, QueryArtifact)
    assert artifact.sql == "DELETE FROM orders"
    assert artifact.status == "BLOCKED_AST"
    assert artifact.error_message == "Chỉ cho phép truy vấn SELECT"


def test_query_response_with_artifacts():
    """Kiểm tra API response schema QueryResponse tích hợp artifacts và artifact_bundle."""
    from src.models.api_schemas import QueryResponse

    artifact = QueryArtifact(
        task_id="t1",
        sql="SELECT 1",
        status="SUCCESS",
        data=[{"1": 1}],
        row_count=1,
    )

    resp = QueryResponse(
        question="Câu hỏi test",
        session_id="session_test",
        answer="Doanh thu ổn định",
        status="COMPLETED",
        artifacts=[artifact],
    )

    dump = resp.model_dump()
    assert dump["session_id"] == "session_test"
    assert len(dump["artifacts"]) == 1
    assert dump["artifacts"][0]["status"] == "SUCCESS"
