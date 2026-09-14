"""Unit tests cho Component 4.2: Subagent Response Synthesizer & Đề Xuất Biểu Đồ."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.agents.prompts.synthesizer_prompt import SYNTHESIZER_SYSTEM_PROMPT
from src.agents.synthesizer import (
    get_synthesizer_subagent,
    response_synthesizer_subagent,
    synthesize_response,
)
from src.models.state import SynthesizerResult


def test_synthesizer_result_pydantic_model():
    """Kiểm tra validation và giá trị mặc định của Pydantic model SynthesizerResult."""
    result = SynthesizerResult(
        chart_type="bar",
        recharts_config={
            "x_key": "c_mktsegment",
            "y_keys": ["total_revenue"],
            "title": "Doanh thu theo phân khúc",
        },
        business_insight="Phân khúc BUILDING chiếm doanh thu cao nhất với hơn 1.5 tỷ.",
        summary_metrics={"total_revenue": 5000000.0, "top_segment": "BUILDING"},
    )

    assert result.chart_type == "bar"
    assert result.recharts_config["x_key"] == "c_mktsegment"
    assert "BUILDING" in result.business_insight
    assert result.summary_metrics["total_revenue"] == 5000000.0

    # Kiểm tra chart_type không hợp lệ
    with pytest.raises(ValidationError):
        SynthesizerResult(
            chart_type="scatter",  # Không nằm trong Literal["bar", "line", "pie", "area", "table"]
            business_insight="Thử nghiệm lỗi",
        )


def test_synthesizer_subagent_dict_structure():
    """Kiểm tra cấu trúc Dictionary của SubAgent Response Synthesizer theo chuẩn DeepAgents."""
    assert isinstance(response_synthesizer_subagent, dict)
    assert response_synthesizer_subagent["name"] == "response-synthesizer"
    assert "trực quan hóa" in response_synthesizer_subagent["description"].lower()
    assert response_synthesizer_subagent["system_prompt"] == SYNTHESIZER_SYSTEM_PROMPT
    assert response_synthesizer_subagent["mode"] == "isolated"
    assert response_synthesizer_subagent["tools"] == []
    assert response_synthesizer_subagent["response_format"] == SynthesizerResult
    assert isinstance(response_synthesizer_subagent["model"], str)
    assert len(response_synthesizer_subagent["model"]) > 0


def test_get_synthesizer_subagent_custom_model():
    """Kiểm tra việc ghi đè tên mô hình trong get_synthesizer_subagent."""
    custom = get_synthesizer_subagent(model="openai:gpt-4o-mini")
    assert custom["name"] == "response-synthesizer"
    assert custom["model"] == "openai:gpt-4o-mini"


def test_synthesize_response_mock_llm_timeseries():
    """Kiểm tra sinh kết quả cho dữ liệu chuỗi thời gian (time-series) -> line chart."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    expected = SynthesizerResult(
        chart_type="line",
        recharts_config={
            "x_key": "order_year",
            "y_keys": ["revenue"],
            "title": "Doanh thu hàng năm giai đoạn 1992 - 1998",
        },
        business_insight="Doanh thu tăng trưởng liên tục từ năm 1992 đến đỉnh điểm năm 1995 đạt 120 tỷ.",
        summary_metrics={"peak_year": 1995, "peak_revenue": 120000000000.0},
    )
    mock_structured.invoke.return_value = expected

    data = [
        {"order_year": 1992, "revenue": 80000000.0},
        {"order_year": 1993, "revenue": 95000000.0},
        {"order_year": 1994, "revenue": 110000000.0},
    ]

    result = synthesize_response(
        question="Doanh thu theo từng năm",
        data=data,
        columns=["order_year", "revenue"],
        llm=mock_llm,
    )

    assert result.chart_type == "line"
    assert result.recharts_config["x_key"] == "order_year"
    assert "tăng trưởng liên tục" in result.business_insight
    mock_llm.with_structured_output.assert_called_once_with(SynthesizerResult)


def test_synthesize_response_mock_llm_bar_chart():
    """Kiểm tra sinh kết quả cho phân bố danh mục -> bar chart."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    expected = SynthesizerResult(
        chart_type="bar",
        recharts_config={
            "x_key": "c_mktsegment",
            "y_keys": ["customer_count"],
            "title": "Phân bố số lượng khách hàng theo thị trường",
        },
        business_insight="Thị trường BUILDING và AUTOMOBILE chiếm đa số khách hàng với hơn 60% tổng số.",
        summary_metrics={"total_customers": 15000},
    )
    mock_structured.invoke.return_value = expected

    data = [
        {"c_mktsegment": "BUILDING", "customer_count": 3010},
        {"c_mktsegment": "AUTOMOBILE", "customer_count": 2980},
        {"c_mktsegment": "MACHINERY", "customer_count": 2950},
    ]

    result = synthesize_response(
        question="Số lượng khách hàng theo từng phân khúc",
        data=data,
        llm=mock_llm,
    )

    assert result.chart_type == "bar"
    assert result.recharts_config["x_key"] == "c_mktsegment"


def test_synthesize_response_empty_data_fast_path():
    """Kiểm tra fast-path: dữ liệu rỗng trả về bảng và không gọi LLM để tiết kiệm token."""
    mock_llm = MagicMock()

    result = synthesize_response(
        question="Doanh thu năm 2025",
        data=[],
        columns=["o_orderdate", "revenue"],
        llm=mock_llm,
    )

    assert result.chart_type == "table"
    assert "không tìm thấy" in result.business_insight.lower()
    assert result.recharts_config == {}
    assert result.summary_metrics == {"total_rows": 0}
    mock_llm.with_structured_output.assert_not_called()


def test_synthesize_response_auto_extracts_columns():
    """Kiểm tra tự động lấy columns từ keys của record đầu tiên nếu không truyền."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    mock_structured.invoke.return_value = SynthesizerResult(
        chart_type="table",
        business_insight="Danh sách 2 đơn hàng mới nhất.",
    )

    data = [
        {"o_orderkey": 1, "o_totalprice": 100.0},
        {"o_orderkey": 2, "o_totalprice": 200.0},
    ]

    result = synthesize_response(
        question="2 đơn hàng gần nhất",
        data=data,
        columns=None,  # Để None để hàm tự suy luận
        llm=mock_llm,
    )

    assert result.chart_type == "table"
    # Kiểm tra prompt được gọi với columns được suy luận
    call_args = mock_structured.invoke.call_args[0][0]
    human_msg_content = call_args[1].content
    assert "o_orderkey" in human_msg_content
    assert "o_totalprice" in human_msg_content


def test_synthesize_response_truncate_large_data():
    """Kiểm tra giới hạn lấy tối đa 50 records đưa vào prompt để tránh tràn context."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    mock_structured.invoke.return_value = SynthesizerResult(
        chart_type="table",
        business_insight="Dữ liệu gồm 100 dòng.",
    )

    large_data = [{"id": i, "val": i * 10} for i in range(100)]

    synthesize_response(
        question="Top 100 bản ghi",
        data=large_data,
        columns=["id", "val"],
        llm=mock_llm,
    )

    call_args = mock_structured.invoke.call_args[0][0]
    human_msg_content = call_args[1].content
    # Đảm bảo phần tử thứ 49 có mặt nhưng phần tử 99 không bị nạp vào chuỗi prompt
    assert "'id': 49" in human_msg_content
    assert "'id': 99" not in human_msg_content


def test_synthesize_response_fallback_on_llm_error():
    """Kiểm tra cơ chế Fail-Safe khi LLM ném ngoại lệ: không làm sập ứng dụng."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.invoke.side_effect = RuntimeError("OpenAI Rate Limit Exceeded")

    data = [{"nation": "VIETNAM", "orders": 500}]

    result = synthesize_response(
        question="Đơn hàng tại Việt Nam",
        data=data,
        columns=["nation", "orders"],
        llm=mock_llm,
    )

    assert result.chart_type == "table"
    assert (
        "Fallback" in result.business_insight or "1 bản ghi" in result.business_insight
    )
    assert result.summary_metrics["total_rows"] == 1


@patch("src.agents.synthesizer.get_chat_model")
def test_synthesize_response_default_llm_initialization(mock_get_chat_model):
    """Kiểm tra việc tự động lấy chat model Tier 2 khi không truyền llm."""
    mock_llm_instance = MagicMock()
    mock_structured = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured
    mock_get_chat_model.return_value = mock_llm_instance

    mock_structured.invoke.return_value = SynthesizerResult(
        chart_type="table",
        business_insight="Hiển thị bảng dữ liệu.",
    )

    result = synthesize_response(
        question="Doanh thu",
        data=[{"rev": 100}],
    )

    assert result.chart_type == "table"
    mock_get_chat_model.assert_called_once()
