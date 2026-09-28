"""Subagent: Schema & Value Retriever (Component 2.3).

Đóng gói theo chuẩn DeepAgents SubAgent dictionary (name="schema-retriever"):
- Chế độ mode: "isolated" (Context Quarantine: cách ly ngữ cảnh thô khỏi Supervisor).
- Mô hình Tier 2 (gpt-4o-mini / claude-3-5-haiku / gemini-2.5-flash) tối ưu tốc độ & chi phí.
- Công cụ: search_tables_and_columns, search_categorical_values.
- Đầu ra có cấu trúc: SchemaContextResult (Pydantic).
"""

from typing import Any, Final

from src.agents.prompts import (
    SCHEMA_RETRIEVER_PROMPT,
    SCHEMA_RETRIEVER_SYSTEM_PROMPT,
)
from src.config import get_settings
from src.models.state import SchemaContextResult
from src.utils.categorical_search import (
    CategoricalMatch,
    find_matching_categorical_values,
    format_categorical_context,
)
from src.utils.schema_context import (
    TPCDS_JOIN_RELATIONSHIPS,
    TPCDS_SEMANTIC_METRICS,
    TPCDS_TABLE_NAMES,
    TPCDS_TABLE_SCHEMAS,
    TPCH_JOIN_RELATIONSHIPS,
    TPCH_SEMANTIC_METRICS,
    TPCH_TABLE_NAMES,
    TPCH_TABLE_SCHEMAS,
    render_schema_context,
)
from src.utils.table_keywords import TABLE_KEYWORD_MAP

# ==============================================================================
# 2. TOOLS CHUYÊN BIỆT CHO SCHEMA RETRIEVER SUBAGENT
# ==============================================================================


def search_tables_and_columns(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    """Tra cứu các bảng và cột TPC-DS có liên quan đến câu hỏi nghiệp vụ.

    Args:
        query: Câu hỏi hoặc từ khóa tìm kiếm của người dùng.
        top_k: Số lượng bảng tối đa trả về (mặc định: 8).

    Returns:
        Danh sách thông tin các bảng khớp kèm mô tả tóm tắt và DDL.
    """
    normalized_query = query.lower()

    # Hỗ trợ cả bảng 24 bảng TPC-DS và 8 bảng TPC-H (nếu có từ khóa legacy)
    all_table_candidates = list(dict.fromkeys(TPCDS_TABLE_NAMES + TPCH_TABLE_NAMES))
    table_scores: dict[str, int] = {tbl: 0 for tbl in all_table_candidates}

    for tbl, keywords in TABLE_KEYWORD_MAP.items():
        if tbl not in table_scores:
            continue
        for kw in keywords:
            if kw in normalized_query:
                table_scores[tbl] += 2
        # Khớp trực tiếp tên bảng
        if tbl in normalized_query:
            table_scores[tbl] += 3

    # Heuristic 1: Yếu tố thời gian (năm, tháng, quý, ngày, số năm cụ thể)
    time_keywords = [
        "năm",
        "nam",
        "tháng",
        "thang",
        "quý",
        "quy",
        "ngày",
        "ngay",
        "year",
        "month",
        "quarter",
        "date",
        "hàng năm",
        "theo tháng",
        "1998",
        "1999",
        "2000",
        "2001",
        "2002",
        "2003",
    ]
    if any(k in normalized_query for k in time_keywords):
        table_scores["date_dim"] += 6

    # Heuristic 2: Điều hướng kênh bán hàng & Đổi trả
    if any(
        k in normalized_query
        for k in ["bán lẻ", "ban le", "cửa hàng", "cua hang", "quầy", "store"]
    ):
        table_scores["store_sales"] += 4
    if any(
        k in normalized_query
        for k in ["trực tuyến", "truc tuyen", "online", "web", "website"]
    ):
        table_scores["web_sales"] += 4
    if any(
        k in normalized_query for k in ["catalog", "danh mục", "danh muc", "bưu điện"]
    ):
        table_scores["catalog_sales"] += 4
    if any(
        k in normalized_query
        for k in ["đổi trả", "doi tra", "hoàn hàng", "hoan hang", "trả lại", "returns"]
    ):
        table_scores["store_returns"] += 3
        table_scores["web_returns"] += 3
        table_scores["reason"] += 2

    # Doanh thu / Lợi nhuận chung -> cộng điểm cả 3 kênh bán
    revenue_keywords = ["doanh thu", "doanh so", "revenue", "lợi nhuận", "chiết khấu"]
    if any(k in normalized_query for k in revenue_keywords):
        table_scores["store_sales"] += 3
        table_scores["web_sales"] += 2
        table_scores["catalog_sales"] += 2
        # Tương thích TPC-H
        table_scores["lineitem"] += 4
        table_scores["orders"] += 3

    # Heuristic 3: Sản phẩm / Mặt hàng
    if any(
        k in normalized_query
        for k in [
            "sản phẩm",
            "san pham",
            "ngành hàng",
            "nganh hang",
            "mặt hàng",
            "mat hang",
            "item",
            "category",
            "brand",
            "thương hiệu",
        ]
    ):
        table_scores["item"] += 4

    # Heuristic 4: Khách hàng, Địa chỉ, Nhân khẩu học
    if any(
        k in normalized_query
        for k in ["khách hàng", "khach hang", "người mua", "customer"]
    ):
        table_scores["customer"] += 3
    if any(
        k in normalized_query
        for k in [
            "địa chỉ",
            "dia chi",
            "tiểu bang",
            "tieu bang",
            "bang",
            "thành phố",
            "state",
            "city",
            "california",
            "texas",
        ]
    ):
        table_scores["customer_address"] += 4
        table_scores["customer"] += 2
    if any(
        k in normalized_query
        for k in [
            "giới tính",
            "gioi tinh",
            "hôn nhân",
            "hon nhan",
            "nam",
            "nữ",
            "kết hôn",
            "gender",
        ]
    ):
        table_scores["customer_demographics"] += 4
        table_scores["customer"] += 2
    if any(
        k in normalized_query
        for k in [
            "thu nhập",
            "thu nhap",
            "hộ gia đình",
            "ho gia dinh",
            "income",
            "household",
        ]
    ):
        table_scores["household_demographics"] += 3
        table_scores["income_band"] += 3

    # Sắp xếp các bảng có score > 0
    ranked_tables = sorted(
        [tbl for tbl, score in table_scores.items() if score > 0],
        key=lambda tbl: table_scores[tbl],
        reverse=True,
    )

    if not ranked_tables:
        # Nếu câu hỏi quá chung chung, fallback trả về top bảng nghiệp vụ cốt lõi
        ranked_tables = ["store_sales", "web_sales", "date_dim", "item", "customer"]

    selected = ranked_tables[:top_k]

    all_schemas = {**TPCH_TABLE_SCHEMAS, **TPCDS_TABLE_SCHEMAS}
    results: list[dict[str, Any]] = []
    for tbl in selected:
        schema = all_schemas.get(tbl, "")
        results.append(
            {
                "table": tbl,
                "relevance_score": table_scores.get(tbl, 0),
                "schema_ddl": schema,
            }
        )

    return results


def search_categorical_values(
    query: str, min_score: float = 65.0, top_k: int = 5
) -> list[dict[str, Any]]:
    """Tra cứu các giá trị danh mục phân loại thực tế (Entity/Value Linking) trong database.

    Args:
        query: Câu hỏi hoặc từ khóa của người dùng.
        min_score: Ngưỡng tương đồng tối thiểu (0-100).
        top_k: Số lượng giá trị danh mục tối đa trả về.

    Returns:
        Danh sách các kết quả khớp: table, column, value, query_keyword, similarity_score, exact_match.
    """
    matches: list[CategoricalMatch] = find_matching_categorical_values(
        query=query,
        top_k=top_k,
        min_score=min_score,
    )

    return [
        {
            "table": m.table,
            "column": m.column,
            "value": m.matched_value,
            "query_keyword": m.query_keyword,
            "similarity_score": m.similarity_score,
            "exact_match": m.exact_match,
        }
        for m in matches
    ]


# ==============================================================================
# 4. HÀM TỔNG HỢP NGỮ CẢNH TRUY VẤN (RETRIEVE_SCHEMA_CONTEXT)
# ==============================================================================


def retrieve_schema_context(
    question: str, selected_tables: list[str] | None = None
) -> SchemaContextResult:
    """Tổng hợp ngữ cảnh lược đồ hoàn chỉnh cho câu hỏi của người dùng.

    Hàm kết hợp:
    1. Tìm bảng liên quan (qua từ khóa hoặc chỉ định trước).
    2. Tìm giá trị danh mục thực tế (Categorical Value Search).
    3. Tự động kết nối các bảng cầu nối (Bridge Tables) để bảo đảm đủ bảng JOIN.
    4. Trích xuất công thức tính toán chỉ số nghiệp vụ (dbt Semantic Metrics).
    5. Kết xuất chuỗi Markdown toàn diện đưa vào prompt cho SQL Generator.

    Args:
        question: Câu hỏi ngôn ngữ tự nhiên của người dùng.
        selected_tables: Danh sách bảng được chỉ định sẵn (nếu có).

    Returns:
        SchemaContextResult chứa bảng, điều kiện join, filter danh mục và Markdown.
    """
    all_schemas = {**TPCH_TABLE_SCHEMAS, **TPCDS_TABLE_SCHEMAS}
    all_joins = list(TPCDS_JOIN_RELATIONSHIPS) + list(TPCH_JOIN_RELATIONSHIPS)
    all_metrics = {**TPCH_SEMANTIC_METRICS, **TPCDS_SEMANTIC_METRICS}

    # 1. Tìm các giá trị danh mục khớp trong câu hỏi
    categorical_matches = find_matching_categorical_values(
        question, top_k=5, min_score=65.0
    )
    # Giữ lại match có độ ưu tiên cao nhất cho mỗi cột (exact match / highest score đứng đầu)
    cat_filters: dict[str, str] = {}
    for m in categorical_matches:
        if m.column not in cat_filters:
            cat_filters[m.column] = m.matched_value

    # 2. Xác định các bảng được chọn
    if selected_tables is not None:
        tables_to_use = [t.lower() for t in selected_tables if t.lower() in all_schemas]
    else:
        found_tables = [
            r["table"] for r in search_tables_and_columns(question, top_k=8)
        ]
        # Bổ sung bảng xuất hiện từ categorical matches
        for m in categorical_matches:
            if m.table not in found_tables:
                found_tables.append(m.table)

        # Đảm bảo tính toàn vẹn quan hệ JOIN (Snowflake Hierarchy Bridge Tables)
        # 1. customer_address -> customer
        if "customer_address" in found_tables and "customer" not in found_tables:
            found_tables.append("customer")
        # 2. customer_demographics -> customer
        if "customer_demographics" in found_tables and "customer" not in found_tables:
            found_tables.append("customer")
        # 3. income_band -> household_demographics -> customer
        if (
            "income_band" in found_tables
            and "household_demographics" not in found_tables
        ):
            found_tables.append("household_demographics")
        if "household_demographics" in found_tables and "customer" not in found_tables:
            found_tables.append("customer")
        # 4. Khi có Fact Sales và có yếu tố thời gian trong câu hỏi -> Bắt buộc gắn date_dim
        sales_facts = {
            "store_sales",
            "web_sales",
            "catalog_sales",
            "store_returns",
            "web_returns",
            "catalog_returns",
            "inventory",
        }
        time_cues = [
            "năm",
            "nam",
            "tháng",
            "thang",
            "quý",
            "quy",
            "ngày",
            "ngay",
            "year",
            "month",
            "date",
            "2000",
            "2001",
            "2002",
            "2003",
        ]
        if (
            "date_dim" not in found_tables
            and any(f in found_tables for f in sales_facts)
            and any(c in question.lower() for c in time_cues)
        ):
            found_tables.append("date_dim")

        # 5. Tương thích TPC-H Bridge Tables
        if "region" in found_tables and "nation" not in found_tables:
            found_tables.append("nation")
        if (
            "customer" in found_tables
            and "lineitem" in found_tables
            and "orders" not in found_tables
        ):
            found_tables.append("orders")
        if (
            "supplier" in found_tables
            and "region" in found_tables
            and "nation" not in found_tables
        ):
            found_tables.append("nation")

        tables_to_use = [t for t in found_tables if t in all_schemas]

    # 3. Trích xuất các điều kiện JOIN giữa các bảng được chọn
    table_set = set(tables_to_use)
    relevant_joins: list[str] = [
        j.condition
        for j in all_joins
        if j.from_table in table_set and j.to_table in table_set
    ]

    # 4. Trích xuất công thức chỉ số nghiệp vụ (dbt Semantic Metrics) liên quan
    metric_formulas: list[str] = []
    for metric in all_metrics.values():
        # Kiểm tra bảng cần thiết của metric có trong tables_to_use không
        if any(tbl in table_set for tbl in metric.required_tables):
            metric_formulas.append(f"{metric.vietnamese_name}: {metric.formula}")

    # 5. Kết xuất Markdown Schema Context
    base_markdown = render_schema_context(tables_to_use)
    categorical_markdown = format_categorical_context(categorical_matches)

    if categorical_markdown:
        context_markdown = f"{base_markdown}\n\n{categorical_markdown}"
    else:
        context_markdown = base_markdown

    return SchemaContextResult(
        selected_tables=tables_to_use,
        join_conditions=relevant_joins,
        categorical_filters=cat_filters,
        metric_formulas=metric_formulas,
        context_markdown=context_markdown,
    )


# ==============================================================================
# 5. KHAI BÁO SUBAGENT DICTIONARY CHUẨN DEEPAGENTS
# ==============================================================================


def get_schema_retriever_subagent(model: str | None = None) -> dict[str, Any]:
    """Tạo cấu hình SubAgent Dictionary cho Schema & Value Retriever.

    Args:
        model: Tùy chọn chỉ định model name (mặc định lấy tier2_model từ Settings).

    Returns:
        Dictionary theo đúng đặc tả DeepAgents SubAgent.
    """
    settings = get_settings()
    active_model = model or settings.tier2_model

    return {
        "name": "schema-retriever",
        "description": (
            "Chuyên tra cứu lược đồ cơ sở dữ liệu TPC-DS 24 bảng (bảng, cột, quan hệ JOIN Snowflake), "
            "công thức chỉ số dbt metrics và các giá trị danh mục phân loại thực tế "
            "(categorical values) tương ứng với câu hỏi nghiệp vụ."
        ),
        "system_prompt": SCHEMA_RETRIEVER_SYSTEM_PROMPT,
        "mode": "isolated",
        "tools": [search_tables_and_columns, search_categorical_values],
        "model": active_model,
        "response_format": SchemaContextResult,
    }


# Instance mặc định dùng sẵn
schema_retriever_subagent: Final[dict[str, Any]] = get_schema_retriever_subagent()

__all__ = [
    "SCHEMA_RETRIEVER_PROMPT",
    "SCHEMA_RETRIEVER_SYSTEM_PROMPT",
    "get_schema_retriever_subagent",
    "retrieve_schema_context",
    "schema_retriever_subagent",
    "search_categorical_values",
    "search_tables_and_columns",
]
