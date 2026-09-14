"""Gói quản lý tập trung toàn bộ Prompt Templates trong hệ thống AI Agent Text-to-SQL.

Các file prompt được phân chia theo từng agent cụ thể:
- error_diagnostic_prompt: Error Diagnostic Agent (Control Pipeline)
- schema_retriever_prompt: Schema & Value Retriever Subagent
"""

from src.agents.prompts.clarification_prompt import (
    CLARIFICATION_HUMAN_PROMPT,
    CLARIFICATION_PROMPT,
    CLARIFICATION_SYSTEM_PROMPT,
)
from src.agents.prompts.error_diagnostic_prompt import (
    ERROR_DIAGNOSTIC_HUMAN_PROMPT,
    ERROR_DIAGNOSTIC_PROMPT,
    ERROR_DIAGNOSTIC_SYSTEM_PROMPT,
)
from src.agents.prompts.schema_retriever_prompt import (
    SCHEMA_RETRIEVER_HUMAN_PROMPT,
    SCHEMA_RETRIEVER_PROMPT,
    SCHEMA_RETRIEVER_SYSTEM_PROMPT,
)
from src.agents.prompts.sql_generator_prompt import (
    DIALECT_RULES_MAP,
    SQL_GENERATOR_HUMAN_PROMPT,
    SQL_GENERATOR_PROMPT,
    SQL_GENERATOR_RETRY_HUMAN_PROMPT,
    SQL_GENERATOR_RETRY_PROMPT,
    SQL_GENERATOR_SYSTEM_PROMPT,
    SUPPORTED_DIALECTS,
    get_dialect_rules,
    transpile_sql,
)
from src.agents.prompts.supervisor_prompt import (
    SUPERVISOR_SYSTEM_PROMPT,
)
from src.agents.prompts.synthesizer_prompt import (
    SYNTHESIZER_HUMAN_PROMPT,
    SYNTHESIZER_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
)

__all__ = [
    "CLARIFICATION_HUMAN_PROMPT",
    "CLARIFICATION_PROMPT",
    "CLARIFICATION_SYSTEM_PROMPT",
    "DIALECT_RULES_MAP",
    "ERROR_DIAGNOSTIC_HUMAN_PROMPT",
    "ERROR_DIAGNOSTIC_PROMPT",
    "ERROR_DIAGNOSTIC_SYSTEM_PROMPT",
    "SCHEMA_RETRIEVER_HUMAN_PROMPT",
    "SCHEMA_RETRIEVER_PROMPT",
    "SCHEMA_RETRIEVER_SYSTEM_PROMPT",
    "SQL_GENERATOR_HUMAN_PROMPT",
    "SQL_GENERATOR_PROMPT",
    "SQL_GENERATOR_RETRY_HUMAN_PROMPT",
    "SQL_GENERATOR_RETRY_PROMPT",
    "SQL_GENERATOR_SYSTEM_PROMPT",
    "SUPERVISOR_SYSTEM_PROMPT",
    "SUPPORTED_DIALECTS",
    "SYNTHESIZER_HUMAN_PROMPT",
    "SYNTHESIZER_PROMPT",
    "SYNTHESIZER_SYSTEM_PROMPT",
    "get_dialect_rules",
    "transpile_sql",
]
