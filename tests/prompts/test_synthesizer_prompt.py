"""Unit tests cho Component 4.2: Synthesizer Prompt Engineering."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agents.prompts.synthesizer_prompt import (
    SYNTHESIZER_HUMAN_PROMPT,
    SYNTHESIZER_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
)


def test_synthesizer_prompt_structure():
    """Kiểm tra cấu trúc ChatPromptTemplate và các thành phần của Synthesizer Prompt."""
    assert isinstance(SYNTHESIZER_PROMPT, ChatPromptTemplate)
    assert len(SYNTHESIZER_PROMPT.messages) == 2

    # Kiểm tra nội dung System Prompt
    system_text = SYNTHESIZER_SYSTEM_PROMPT.lower()
    assert "chuyên gia" in system_text
    assert "trực quan hóa" in system_text or "biểu đồ" in system_text
    assert "recharts" in system_text
    assert "bar" in system_text
    assert "line" in system_text
    assert "pie" in system_text
    assert "area" in system_text
    assert "table" in system_text
    assert "tiếng việt" in system_text

    # Kiểm tra biến đầu vào của Human Prompt
    assert "{question}" in SYNTHESIZER_HUMAN_PROMPT
    assert "{columns}" in SYNTHESIZER_HUMAN_PROMPT
    assert "{data_records}" in SYNTHESIZER_HUMAN_PROMPT
    assert set(SYNTHESIZER_PROMPT.input_variables) == {
        "question",
        "columns",
        "data_records",
    }


def test_synthesizer_prompt_format_messages():
    """Kiểm tra render messages từ template với dữ liệu bảng mẫu."""
    question = "Top 3 khách hàng chi tiêu nhiều nhất năm 1995"
    columns = ["c_name", "total_spend"]
    data_records = [
        {"c_name": "Customer#000000001", "total_spend": 1500000.0},
        {"c_name": "Customer#000000002", "total_spend": 1200000.0},
        {"c_name": "Customer#000000003", "total_spend": 980000.0},
    ]

    messages = SYNTHESIZER_PROMPT.format_messages(
        question=question,
        columns=str(columns),
        data_records=str(data_records),
    )

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert question in messages[1].content
    assert "Customer#000000001" in messages[1].content
    assert "total_spend" in messages[1].content
