"""Gói quản lý tập trung toàn bộ Prompt Templates trong hệ thống AI Agent Text-to-SQL.

Các prompt được tổ chức theo từng agent/node chuyên trách:
- analytics_planner_prompt: Analysis Planner Node (Component 2.2)
- analytics_presentation_prompt: Presentation Node (Component 2.5 / Phase 3)
- clarification_prompt: Intent & Ambiguity Check (Component 4.1)
- error_diagnostic_prompt: Error Diagnostic Agent (Control Pipeline)
- evidence_analyzer_prompt: Evidence Analyzer Node (Component 2.4)
- schema_retriever_prompt: Schema & Value Retriever Subagent
- sql_generator_prompt: SQL Generator Subagent & Dialect Rules
- supervisor_prompt: Deep Agent Supervisor (Architecture v4.0)
- synthesizer_prompt: Response Synthesizer Subagent (Recharts & Insight)
"""

from src.agents.prompts.analytics_planner_prompt import (
    ANALYTICS_PLANNER_HUMAN_PROMPT,
    ANALYTICS_PLANNER_PROMPT,
    ANALYTICS_PLANNER_SYSTEM_PROMPT,
)
from src.agents.prompts.analytics_presentation_prompt import (
    ANALYTICS_PRESENTATION_HUMAN_PROMPT,
    ANALYTICS_PRESENTATION_PROMPT,
    ANALYTICS_PRESENTATION_SYSTEM_PROMPT,
)
from src.agents.prompts.clarification_prompt import (
    CLARIFICATION_HUMAN_PROMPT,
    CLARIFICATION_PROMPT,
    CLARIFICATION_SYSTEM_PROMPT,
)
from src.agents.prompts.consultation_prompt import (
    CONSULTATION_SYSTEM_PROMPT,
)
from src.agents.prompts.error_diagnostic_prompt import (
    ERROR_DIAGNOSTIC_HUMAN_PROMPT,
    ERROR_DIAGNOSTIC_PROMPT,
    ERROR_DIAGNOSTIC_SYSTEM_PROMPT,
)
from src.agents.prompts.evidence_analyzer_prompt import (
    EVIDENCE_ANALYZER_HUMAN_PROMPT,
    EVIDENCE_ANALYZER_PROMPT,
    EVIDENCE_ANALYZER_SYSTEM_PROMPT,
)
from src.agents.prompts.preflight_prompt import (
    PREFLIGHT_GATEKEEPER_HUMAN_PROMPT,
    PREFLIGHT_GATEKEEPER_PROMPT,
    PREFLIGHT_GATEKEEPER_SYSTEM_PROMPT,
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
    "ANALYTICS_PLANNER_HUMAN_PROMPT",
    "ANALYTICS_PLANNER_PROMPT",
    "ANALYTICS_PLANNER_SYSTEM_PROMPT",
    "ANALYTICS_PRESENTATION_HUMAN_PROMPT",
    "ANALYTICS_PRESENTATION_PROMPT",
    "ANALYTICS_PRESENTATION_SYSTEM_PROMPT",
    "CLARIFICATION_HUMAN_PROMPT",
    "CLARIFICATION_PROMPT",
    "CLARIFICATION_SYSTEM_PROMPT",
    "CONSULTATION_SYSTEM_PROMPT",
    "DIALECT_RULES_MAP",
    "ERROR_DIAGNOSTIC_HUMAN_PROMPT",
    "ERROR_DIAGNOSTIC_PROMPT",
    "ERROR_DIAGNOSTIC_SYSTEM_PROMPT",
    "EVIDENCE_ANALYZER_HUMAN_PROMPT",
    "EVIDENCE_ANALYZER_PROMPT",
    "EVIDENCE_ANALYZER_SYSTEM_PROMPT",
    "PREFLIGHT_GATEKEEPER_HUMAN_PROMPT",
    "PREFLIGHT_GATEKEEPER_PROMPT",
    "PREFLIGHT_GATEKEEPER_SYSTEM_PROMPT",
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
