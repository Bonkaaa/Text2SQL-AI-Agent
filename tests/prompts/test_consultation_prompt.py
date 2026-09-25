"""Unit tests cho Consultation Prompt Engineering (Component consultation-agent)."""

from src.agents.prompts.consultation_prompt import CONSULTATION_SYSTEM_PROMPT


def test_consultation_prompt_structure():
    """Kiểm tra cấu trúc và tính toàn vẹn của Consultation System Prompt."""
    assert isinstance(CONSULTATION_SYSTEM_PROMPT, str)
    assert len(CONSULTATION_SYSTEM_PROMPT) > 500

    prompt = CONSULTATION_SYSTEM_PROMPT
    prompt_lower = prompt.lower()

    # 1. Kiểm tra vai trò
    assert "consultation" in prompt_lower or "tư vấn" in prompt_lower or "giải đáp" in prompt_lower
    assert "tpc-h" in prompt_lower

    # 2. Kiểm tra phân loại 2 hành vi chính: Chào hỏi vs Tra cứu Schema/Catalog
    assert "chào hỏi" in prompt_lower or "xã giao" in prompt_lower
    assert "tra cứu" in prompt_lower

    # 3. Kiểm tra danh mục 3 Metadata Tools
    assert "search_tables_and_columns" in prompt
    assert "get_column_samples_and_values" in prompt
    assert "search_business_definition" in prompt

    # 4. Kiểm tra tham số & hướng dẫn khi nào dùng
    assert "query" in prompt
    assert "table_name" in prompt
    assert "column_name" in prompt
    assert "metric_query" in prompt
    assert "khi nào dùng" in prompt_lower
    assert "hướng dẫn sử dụng" in prompt_lower

    # 5. Kiểm tra quy trình thực hiện
    assert "quy trình" in prompt_lower
    assert "không sinh sql" in prompt_lower or "không cần sinh sql" in prompt_lower
