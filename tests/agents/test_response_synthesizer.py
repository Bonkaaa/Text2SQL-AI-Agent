"""Unit tests cho ResponseSynthesizer & Composable ResponsePackage (Phase 3).

Kiểm thử:
1. Fast-path fallback khi danh sách artifacts rỗng hoặc toàn bộ query failed (Zero LLM token).
2. Trích xuất và hydrate KPI Card từ mảng dữ liệu thật.
3. Trích xuất và hydrate Chart và Table bảo đảm 100% tính toàn vẹn dữ liệu (Zero Hallucination).
4. Tổ hợp linh hoạt Mini-Dashboard (nhiều KPI + Chart + Table).
5. Fail-safe fallback khi LLM gặp lỗi mạng/API error.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.analytics.response_synthesizer import ResponseSynthesizer
from src.models.artifacts import (
    ArtifactSpec,
    CalloutArtifact,
    ChartArtifact,
    KpiArtifact,
    QueryArtifact,
    ResponsePackage,
    SynthesisDecision,
    TableArtifact,
)


@pytest.fixture
def mock_successful_artifact():
    return QueryArtifact(
        task_id="task_1",
        sql="SELECT l_shipmode, sum(l_extendedprice) as revenue FROM lineitem GROUP BY 1",
        status="SUCCESS",
        data=[
            {"l_shipmode": "AIR", "revenue": 120500.0},
            {"l_shipmode": "SHIP", "revenue": 340000.0},
            {"l_shipmode": "TRUCK", "revenue": 89000.0},
        ],
        columns=["l_shipmode", "revenue"],
        row_count=3,
        execution_time_ms=12.5,
    )


@pytest.fixture
def mock_second_artifact():
    return QueryArtifact(
        task_id="task_2",
        sql="SELECT count(*) as total_orders, sum(o_totalprice) as total_value FROM orders",
        status="SUCCESS",
        data=[{"total_orders": 1500, "total_value": 549500.0}],
        columns=["total_orders", "total_value"],
        row_count=1,
        execution_time_ms=8.2,
    )


@pytest.fixture
def mock_failed_artifact():
    return QueryArtifact(
        task_id="task_err",
        sql="SELECT * FROM non_existent_table",
        status="DB_ERROR",
        data=[],
        columns=[],
        row_count=0,
        error_message="Table not found: non_existent_table",
    )


@pytest.mark.asyncio
async def test_synthesize_fast_path_empty_artifacts():
    """Kiểm tra fast-path khi không có artifact nào: Trả về CalloutArtifact 'no_data', không gọi LLM."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()

    synthesizer = ResponseSynthesizer(model=mock_llm)
    result = await synthesizer.synthesize(
        question="Doanh thu là bao nhiêu?",
        artifacts=[],
        session_id="session_test_empty",
    )

    assert isinstance(result, ResponsePackage)
    assert result.session_id == "session_test_empty"
    assert len(result.artifacts) == 1
    assert isinstance(result.artifacts[0], CalloutArtifact)
    assert result.artifacts[0].variant == "no_data"
    assert "Không tìm thấy dữ liệu" in result.direct_answer
    # Đảm bảo không gọi LLM
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_fast_path_all_failed_artifacts(mock_failed_artifact):
    """Kiểm tra fast-path khi toàn bộ artifacts đều thất bại: Trả về CalloutArtifact 'error'."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()

    synthesizer = ResponseSynthesizer(model=mock_llm)
    result = await synthesizer.synthesize(
        question="Doanh thu theo vùng?",
        artifacts=[mock_failed_artifact],
        session_id="session_test_fail",
    )

    assert isinstance(result, ResponsePackage)
    assert len(result.artifacts) == 1
    assert isinstance(result.artifacts[0], CalloutArtifact)
    assert result.artifacts[0].variant == "error"
    assert "thất bại" in result.direct_answer
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_kpi_only(mock_second_artifact):
    """Kiểm tra kịch bản câu hỏi chỉ số đơn: Sinh 1 KPI Card với giá trị được trích xuất chính xác."""
    decision = SynthesisDecision(
        direct_answer="Tổng số đơn hàng là 1,500 đơn với tổng giá trị xấp xỉ 549,500 USD.",
        detailed_insight=["Quy mô đơn hàng trung bình đạt khoảng 366 USD/đơn."],
        selected_artifacts=[
            ArtifactSpec(
                artifact_type="kpi",
                target_task_id="task_2",
                kpi_title="Tổng số lượng đơn",
                kpi_metric_column="total_orders",
                kpi_unit="Đơn hàng",
            )
        ],
    )

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=decision)
    mock_llm.with_structured_output.return_value = mock_structured

    synthesizer = ResponseSynthesizer(model=mock_llm)
    result = await synthesizer.synthesize(
        question="Có bao nhiêu đơn hàng?",
        artifacts=[mock_second_artifact],
        session_id="session_kpi",
    )

    assert isinstance(result, ResponsePackage)
    assert result.direct_answer == decision.direct_answer
    assert result.layout == "focus"
    assert len(result.artifacts) == 1
    kpi = result.artifacts[0]
    assert isinstance(kpi, KpiArtifact)
    assert kpi.title == "Tổng số lượng đơn"
    assert kpi.value == 1500
    assert kpi.unit == "Đơn hàng"


@pytest.mark.asyncio
async def test_synthesize_chart_and_table_hydration(mock_successful_artifact):
    """Kiểm tra cơ chế Data Hydration: Mảng data thật được rót chính xác 100% vào Chart và Table."""
    decision = SynthesisDecision(
        direct_answer="Phương thức vận chuyển đường biển (SHIP) chiếm tỷ trọng doanh thu áp đảo.",
        detailed_insight=[
            "SHIP đạt 340,000 USD doanh thu, cao gấp gần 3 lần AIR.",
            "TRUCK có doanh thu thấp nhất ở mức 89,000 USD.",
        ],
        selected_artifacts=[
            ArtifactSpec(
                artifact_type="chart",
                target_task_id="task_1",
                chart_type="bar",
                chart_title="Doanh thu theo phương thức vận chuyển",
                x_axis_column="l_shipmode",
                y_axis_columns=["revenue"],
                series_labels={"revenue": "Doanh thu (USD)"},
            ),
            ArtifactSpec(
                artifact_type="table",
                target_task_id="task_1",
                table_title="Chi tiết doanh thu vận chuyển",
                display_columns=["l_shipmode", "revenue"],
            ),
        ],
    )

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=decision)
    mock_llm.with_structured_output.return_value = mock_structured

    synthesizer = ResponseSynthesizer(model=mock_llm)
    result = await synthesizer.synthesize(
        question="So sánh doanh thu giữa các phương thức giao hàng",
        artifacts=[mock_successful_artifact],
        session_id="session_chart_table",
    )

    assert len(result.artifacts) == 2

    # Kiểm tra ChartArtifact
    chart = result.artifacts[0]
    assert isinstance(chart, ChartArtifact)
    assert chart.chart_type == "bar"
    assert chart.x_key == "l_shipmode"
    assert chart.y_keys == ["revenue"]
    assert chart.series_labels == {"revenue": "Doanh thu (USD)"}
    # Dữ liệu phải khớp 100% với QueryArtifact.data
    assert chart.data == mock_successful_artifact.data

    # Kiểm tra TableArtifact
    table = result.artifacts[1]
    assert isinstance(table, TableArtifact)
    assert table.columns == ["l_shipmode", "revenue"]
    assert table.rows == mock_successful_artifact.data
    assert table.total_row_count == 3


@pytest.mark.asyncio
async def test_synthesize_multi_artifact_dashboard(
    mock_successful_artifact, mock_second_artifact
):
    """Kiểm tra tổ hợp Mini-Dashboard: 2 KPIs + 1 Chart + 1 Table xếp bố cục dashboard_grid."""
    decision = SynthesisDecision(
        direct_answer="Báo cáo vận hành chuỗi cung ứng TPC-H ghi nhận hiệu suất tăng trưởng tích cực.",
        detailed_insight=[
            "Tổng giá trị đơn hàng vượt ngưỡng 500,000 USD.",
            "Doanh số tập trung mạnh vào phương thức vận chuyển SHIP.",
        ],
        selected_artifacts=[
            ArtifactSpec(
                artifact_type="kpi",
                target_task_id="task_2",
                kpi_title="Tổng giá trị đơn hàng",
                kpi_metric_column="total_value",
                kpi_unit="USD",
            ),
            ArtifactSpec(
                artifact_type="kpi",
                target_task_id="task_2",
                kpi_title="Số lượng đơn",
                kpi_metric_column="total_orders",
                kpi_unit="Đơn",
            ),
            ArtifactSpec(
                artifact_type="chart",
                target_task_id="task_1",
                chart_type="bar",
                chart_title="Doanh thu theo hình thức vận chuyển",
                x_axis_column="l_shipmode",
                y_axis_columns=["revenue"],
            ),
            ArtifactSpec(
                artifact_type="table",
                target_task_id="task_1",
                table_title="Bảng kê chi tiết",
            ),
        ],
    )

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=decision)
    mock_llm.with_structured_output.return_value = mock_structured

    synthesizer = ResponseSynthesizer(model=mock_llm)
    result = await synthesizer.synthesize(
        question="Tổng quan tình hình đơn hàng và vận chuyển",
        artifacts=[mock_successful_artifact, mock_second_artifact],
        session_id="session_dashboard",
    )

    assert result.layout == "dashboard_grid"
    assert len(result.artifacts) == 4
    assert isinstance(result.artifacts[0], KpiArtifact)
    assert isinstance(result.artifacts[1], KpiArtifact)
    assert isinstance(result.artifacts[2], ChartArtifact)
    assert isinstance(result.artifacts[3], TableArtifact)
    assert len(result.executed_queries) == 2


@pytest.mark.asyncio
async def test_synthesize_llm_failure_fallback(mock_successful_artifact):
    """Kiểm tra cơ chế Fail-Safe: Khi LLM gặp ngoại lệ, tự động tạo Table fallback an toàn."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        side_effect=RuntimeError("Google Gemini API timeout")
    )
    mock_llm.with_structured_output.return_value = mock_structured

    synthesizer = ResponseSynthesizer(model=mock_llm)
    result = await synthesizer.synthesize(
        question="Doanh thu vận chuyển",
        artifacts=[mock_successful_artifact],
        session_id="session_fallback",
    )

    assert isinstance(result, ResponsePackage)
    assert "Đã hoàn thành truy vấn" in result.direct_answer
    assert len(result.artifacts) >= 1
    assert isinstance(result.artifacts[0], TableArtifact)
    assert result.artifacts[0].rows == mock_successful_artifact.data
