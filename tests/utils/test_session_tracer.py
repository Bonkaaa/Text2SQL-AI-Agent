"""Unit tests cho Session Execution Tracer & Artifacts Logger."""

import json
from unittest.mock import patch

from src.models.state import SynthesizerResult
from src.utils.session_tracer import SessionTracer


def test_tracer_creates_directory_structure(tmp_path):
    """Kiểm tra SessionTracer tạo đúng cấu trúc thư mục {timestamp}_{session_id[:8]}."""
    session_id = "session-abc-12345678"
    tracer = SessionTracer(session_id=session_id, base_dir=tmp_path)

    trace_dir = tracer.get_trace_dir()
    assert trace_dir.exists()
    assert trace_dir.is_dir()
    # Kiểm tra tên thư mục có dạng YYYYMMDD_HHMMSS_session-
    assert "session-" in trace_dir.name
    assert str(tmp_path) in str(trace_dir)


def test_tracer_log_text_and_sql_artifacts(tmp_path):
    """Kiểm tra ghi tệp .md và .sql giữ nguyên định dạng và font tiếng Việt UTF-8."""
    tracer = SessionTracer(session_id="session-test-text", base_dir=tmp_path)

    # Ghi Markdown context
    md_content = "# Ngữ cảnh Lược đồ\n- Bảng: `orders`, `customer`\n- Phân khúc: Ô tô"
    md_path = tracer.log_artifact("02_schema_context.md", md_content)

    assert md_path is not None
    assert md_path.exists()
    assert md_path.read_text(encoding="utf-8") == md_content

    # Ghi SQL nháp
    sql_content = "SELECT c_name, count(*) FROM customer GROUP BY c_name LIMIT 10;"
    sql_path = tracer.log_artifact("03_draft_sql.sql", sql_content)

    assert sql_path is not None
    assert sql_path.exists()
    assert sql_path.read_text(encoding="utf-8") == sql_content


def test_tracer_log_json_dict_and_pydantic_model(tmp_path):
    """Kiểm tra ghi dữ liệu dict và Pydantic model sang file .json chuẩn UTF-8."""
    tracer = SessionTracer(session_id="session-test-json", base_dir=tmp_path)

    # Ghi Dict thông thường
    question_data = {
        "question": "Top 5 khách hàng năm 1995",
        "role": "Analyst",
        "dialect": "duckdb",
    }
    q_path = tracer.log_artifact("00_question.json", question_data)
    assert q_path is not None
    assert q_path.exists()

    with open(q_path, encoding="utf-8") as f:
        loaded_q = json.load(f)
    assert loaded_q["question"] == "Top 5 khách hàng năm 1995"
    assert loaded_q["role"] == "Analyst"

    # Ghi Pydantic Model (SynthesizerResult)
    synth_result = SynthesizerResult(
        chart_type="bar",
        recharts_config={"x_key": "customer", "y_keys": ["revenue"]},
        business_insight="Doanh thu tăng trưởng mạnh mẽ trong năm 1995.",
        summary_metrics={"total_revenue": 1500000.0},
    )
    synth_path = tracer.log_artifact("06_synthesizer.json", synth_result)
    assert synth_path is not None
    assert synth_path.exists()

    with open(synth_path, encoding="utf-8") as f:
        loaded_synth = json.load(f)
    assert loaded_synth["chart_type"] == "bar"
    assert "tăng trưởng mạnh mẽ" in loaded_synth["business_insight"]
    assert loaded_synth["summary_metrics"]["total_revenue"] == 1500000.0


def test_tracer_log_summary_metadata(tmp_path):
    """Kiểm tra ghi tệp metadata.json tóm tắt phiên truy vấn."""
    tracer = SessionTracer(session_id="session-test-meta", base_dir=tmp_path)

    meta_path = tracer.log_summary(
        status="SUCCESS",
        total_time_ms=450.5,
        retry_count=1,
        question="Doanh thu 1995",
    )

    assert meta_path is not None
    assert meta_path.exists()
    assert meta_path.name == "metadata.json"

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["status"] == "SUCCESS"
    assert meta["total_time_ms"] == 450.5
    assert meta["retry_count"] == 1
    assert meta["question"] == "Doanh thu 1995"
    assert "timestamp" in meta


def test_tracer_disabled_toggle(tmp_path):
    """Kiểm tra khi enabled=False thì không tạo thư mục và không ghi bất kỳ tệp nào."""
    tracer = SessionTracer(
        session_id="session-disabled",
        base_dir=tmp_path,
        enabled=False,
    )

    res_path = tracer.log_artifact("test.txt", "Nội dung mẫu")
    assert res_path is None

    # Không có thư mục con nào được tạo ra trong tmp_path
    subdirs = list(tmp_path.iterdir())
    assert len(subdirs) == 0


def test_tracer_fail_safe_on_io_error(tmp_path):
    """Kiểm tra cơ chế Fail-Safe: không ném ngoại lệ khi gặp sự cố I/O đĩa."""
    tracer = SessionTracer(session_id="session-io-error", base_dir=tmp_path)

    with patch("pathlib.Path.write_text", side_effect=OSError("Disk write error")):
        result = tracer.log_artifact("error.txt", "Dữ liệu lỗi")
        # Fail-Safe trả về None mà không crash
        assert result is None
