"""Unit tests cho Component 4.3: Supervisor Prompt Engineering."""

from src.agents.prompts import SUPERVISOR_SYSTEM_PROMPT
from src.agents.prompts.supervisor_prompt import (
    SUPERVISOR_SYSTEM_PROMPT as DIRECT_SUPERVISOR_PROMPT,
)


def test_supervisor_prompt_structure_and_reexport():
    """Kiểm tra nội dung hướng dẫn điều phối và tính toàn vẹn của Supervisor System Prompt."""
    assert SUPERVISOR_SYSTEM_PROMPT == DIRECT_SUPERVISOR_PROMPT
    assert isinstance(SUPERVISOR_SYSTEM_PROMPT, str)
    assert len(SUPERVISOR_SYSTEM_PROMPT) > 500

    prompt_lower = SUPERVISOR_SYSTEM_PROMPT.lower()

    # 1. Kiểm tra vai trò
    assert "supervisor" in prompt_lower
    assert "tpc-h" in prompt_lower

    # 2. Kiểm tra danh sách 4 Subagents
    assert "schema-retriever" in prompt_lower
    assert "sql-generator" in prompt_lower
    assert "control-pipeline" in prompt_lower
    assert "response-synthesizer" in prompt_lower

    # 3. Kiểm tra quy trình và công cụ cốt lõi
    assert "write_todos" in prompt_lower
    assert "task(" in prompt_lower
    assert "clarification" in prompt_lower
    assert "3 lần" in prompt_lower or "self-correction" in prompt_lower

    # 4. Kiểm tra nguyên tắc an toàn
    assert "select" in prompt_lower
    assert "chỉ cho phép truy vấn đọc" in prompt_lower or "chỉ cho phép" in prompt_lower
