"""Bộ 4 Strategic Metadata Tools cho SQL Generator và Direct Chat Node (Component 2.3.1).

Cung cấp các công cụ tra cứu siêu dữ liệu tất định và ngữ nghĩa nghiệp vụ:
1. search_tables_and_columns: Tra cứu DDL và cấu trúc bảng theo từ khóa
2. get_column_samples_and_values: Lấy danh mục giá trị thực tế của các cột phân loại
3. find_join_path: Tìm đường nối khóa ngoại ngắn nhất và bảng cầu nối qua thuật toán BFS
4. search_business_definition: Tra cứu công thức tính dbt Semantic Metrics chuẩn hóa
"""

from __future__ import annotations

from collections import deque
from typing import Any

from langchain_core.tools import tool

from src.agents.schema_retriever import (
    search_tables_and_columns as _internal_search_tables,
)
from src.utils.categorical_search import find_matching_categorical_values
from src.utils.schema_context import (
    TPCH_JOIN_RELATIONSHIPS,
    TPCH_SEMANTIC_METRICS,
    TPCH_TABLE_NAMES,
)

# Từ điển giá trị danh mục phân loại chuẩn trong TPC-H Benchmark
TPCH_CATEGORICAL_CATALOG: dict[str, dict[str, list[str]]] = {
    "customer": {
        "c_mktsegment": [
            "AUTOMOBILE",
            "BUILDING",
            "FURNITURE",
            "HOUSEHOLD",
            "MACHINERY",
        ],
    },
    "orders": {
        "o_orderstatus": ["O", "F", "P"],
        "o_orderpriority": [
            "1-URGENT",
            "2-HIGH",
            "3-MEDIUM",
            "4-NOT SPECIFIED",
            "5-LOW",
        ],
    },
    "lineitem": {
        "l_returnflag": ["R", "A", "N"],
        "l_linestatus": ["O", "F"],
        "l_shipmode": ["AIR", "FOB", "MAIL", "RAIL", "REG AIR", "SHIP", "TRUCK"],
        "l_shipinstruct": ["DELIVER IN PERSON", "TAKE BACK RETURN", "NONE"],
    },
    "region": {
        "r_name": ["AFRICA", "AMERICA", "ASIA", "EUROPE", "MIDDLE EAST"],
    },
    "nation": {
        "n_name": [
            "ALGERIA",
            "ARGENTINA",
            "BRAZIL",
            "CANADA",
            "EGYPT",
            "ETHIOPIA",
            "FRANCE",
            "GERMANY",
            "INDIA",
            "INDONESIA",
            "IRAN",
            "IRAQ",
            "JAPAN",
            "JORDAN",
            "KENYA",
            "MOROCCO",
            "MOZAMBIQUE",
            "PERU",
            "CHINA",
            "ROMANIA",
            "SAUDI ARABIA",
            "VIETNAM",
            "RUSSIA",
            "UNITED KINGDOM",
            "UNITED STATES",
        ]
    },
}


# ==============================================================================
# 1. SEARCH TABLES AND COLUMNS
# ==============================================================================


def search_tables_and_columns(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Tra cứu DDL và cấu trúc các bảng, cột trong cơ sở dữ liệu TPC-H liên quan đến từ khóa.

    Args:
        query: Tên bảng, tên cột hoặc từ khóa nghiệp vụ cần tra cứu (ví dụ: 'lineitem', 'doanh thu đơn hàng').
        top_k: Số lượng bảng tối đa trả về (mặc định 5).

    Returns:
        Danh sách thông tin các bảng khớp kèm DDL và điểm tương quan.
    """
    return _internal_search_tables(query=query, top_k=top_k)


# ==============================================================================
# 2. GET COLUMN SAMPLES AND VALUES
# ==============================================================================


def get_column_samples_and_values(
    table: str, column: str, query: str = ""
) -> dict[str, Any]:
    """Tra cứu các giá trị danh mục thực tế (distinct categorical values) có trong cơ sở dữ liệu.

    Sử dụng tool này khi cần viết mệnh đề WHERE lọc theo phân khúc, trạng thái, khu vực,
    phương thức vận chuyển để tránh tuyệt đối việc đoán mò giá trị literal.

    Args:
        table: Tên bảng cần tra cứu (ví dụ: 'customer', 'orders', 'region', 'lineitem').
        column: Tên cột cần tra cứu (ví dụ: 'c_mktsegment', 'o_orderstatus', 'r_name', 'l_shipmode').
        query: Từ khóa giá trị tùy chọn để lọc nhanh (ví dụ: 'asia', 'building').

    Returns:
        Dictionary chứa trạng thái, tên bảng, tên cột và danh sách giá trị thực tế.
    """
    tbl = table.lower().strip()
    col = column.lower().strip()

    # 1. Kiểm tra trong catalog danh mục TPC-H có sẵn
    table_catalog = TPCH_CATEGORICAL_CATALOG.get(tbl, {})
    if col in table_catalog:
        values = list(table_catalog[col])
        if query and query.strip():
            q_clean = query.lower().strip()
            # Lọc các giá trị khớp chuỗi hoặc từ khóa
            filtered = [v for v in values if q_clean in v.lower()]
            if not filtered:
                # Tìm kiếm tương đối qua vector / fuzzy search
                fuzzy_matches = find_matching_categorical_values(query, top_k=5)
                filtered = [
                    m.matched_value
                    for m in fuzzy_matches
                    if m.table == tbl and m.column == col
                ]
            values = filtered or values

        return {
            "status": "SUCCESS",
            "table": tbl,
            "column": col,
            "values": values,
            "description": f"Tìm thấy {len(values)} giá trị danh mục hợp lệ trong cột {col}.",
        }

    # 2. Thử tìm qua ChromaDB Fuzzy Categorical Search
    if query and query.strip():
        fuzzy_matches = find_matching_categorical_values(query, top_k=5)
        matched_values = [
            m.matched_value
            for m in fuzzy_matches
            if (not tbl or m.table == tbl) and (not col or m.column == col)
        ]
        if matched_values:
            return {
                "status": "SUCCESS",
                "table": tbl,
                "column": col,
                "values": matched_values,
                "description": f"Tìm thấy {len(matched_values)} giá trị qua Entity Linking.",
            }

    return {
        "status": "NOT_FOUND",
        "table": tbl,
        "column": col,
        "values": [],
        "description": f"Không tìm thấy danh mục giá trị chuẩn cho cột '{col}' trong bảng '{tbl}'.",
    }


# ==============================================================================
# 3. FIND JOIN PATH (BREADTH-FIRST SEARCH GRAPH)
# ==============================================================================


def find_join_path(table_a: str, table_b: str) -> dict[str, Any]:
    """Tìm lộ trình JOIN ngắn nhất và điều kiện khóa ngoại chính xác giữa hai bảng trong cơ sở dữ liệu.

    Sử dụng tool này khi cần truy vấn kết hợp nhiều bảng mà chưa rõ các khóa ngoại
    hoặc cần xác định bảng cầu nối (Bridge Tables) trung gian.

    Args:
        table_a: Tên bảng nguồn (ví dụ: 'customer').
        table_b: Tên bảng đích (ví dụ: 'part' hoặc 'region').

    Returns:
        Dictionary chứa danh sách chuỗi bảng, các mệnh đề JOIN và các bảng trung gian cần thiết.
    """
    tbl_a = table_a.lower().strip()
    tbl_b = table_b.lower().strip()

    valid_tables = set(TPCH_TABLE_NAMES)
    if tbl_a not in valid_tables or tbl_b not in valid_tables:
        return {
            "found": False,
            "error": f"Bảng '{table_a}' hoặc '{table_b}' không tồn tại trong 8 bảng TPC-H: {sorted(valid_tables)}",
        }

    if tbl_a == tbl_b:
        return {
            "found": True,
            "tables_chain": [tbl_a],
            "join_conditions": [],
            "bridge_tables_needed": [],
            "description": f"Hai bảng trùng nhau ({tbl_a}), không cần phép JOIN.",
        }

    # Xây dựng đồ thị vô hướng từ TPCH_JOIN_RELATIONSHIPS
    graph: dict[str, list[tuple[str, str]]] = {tbl: [] for tbl in TPCH_TABLE_NAMES}
    for rel in TPCH_JOIN_RELATIONSHIPS:
        graph[rel.from_table].append((rel.to_table, rel.condition))
        graph[rel.to_table].append((rel.from_table, rel.condition))

    # Chạy BFS để tìm đường đi ngắn nhất từ tbl_a đến tbl_b
    queue: deque[tuple[str, list[str], list[str]]] = deque([(tbl_a, [tbl_a], [])])
    visited = {tbl_a}

    while queue:
        current, path, conditions = queue.popleft()

        if current == tbl_b:
            bridge_tables = path[1:-1]
            return {
                "found": True,
                "tables_chain": path,
                "join_conditions": conditions,
                "bridge_tables_needed": bridge_tables,
                "description": f"Tìm thấy lộ trình JOIN qua {len(path)} bảng: {' -> '.join(path)}.",
            }

        for neighbor, condition in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor], conditions + [condition]))

    return {
        "found": False,
        "error": f"Không tìm thấy lộ trình JOIN giữa bảng '{tbl_a}' và '{tbl_b}'.",
    }


# ==============================================================================
# 4. SEARCH BUSINESS DEFINITION (SEMANTIC METRICS LAYER)
# ==============================================================================


def search_business_definition(query: str) -> dict[str, Any]:
    """Tra cứu định nghĩa chỉ số nghiệp vụ chuẩn hóa (dbt Semantic Metrics) và công thức SQL.

    Sử dụng tool này khi câu hỏi đề cập đến các chỉ số kinh doanh như doanh thu thuần,
    doanh thu gộp, lợi nhuận, tỷ lệ hoàn hàng, tỷ lệ giao hàng trễ... để lấy công thức chuẩn
    thay vì tự phỏng đoán công thức toán học.

    Args:
        query: Tên chỉ số hoặc khái niệm kinh doanh (ví dụ: 'doanh thu thuần', 'lợi nhuận', 'hoàn hàng').

    Returns:
        Dictionary chứa ID chỉ số, tên tiếng Việt, công thức SQL chuẩn, bảng yêu cầu và mô tả.
    """
    q_norm = query.lower().strip()
    stop_words = {"chỉ", "số", "các", "những", "của", "và", "trong", "cho", "được", "là", "theo", "tại"}

    best_metric = None
    best_score = 0

    # Chấm điểm độ tương đồng từ khóa
    for metric_id, metric in TPCH_SEMANTIC_METRICS.items():
        score = 0
        name_lower = metric.vietnamese_name.lower()

        if q_norm == metric_id or q_norm == name_lower:
            score += 30
        elif name_lower in q_norm or q_norm in name_lower:
            score += 15

        # Khớp các từ đơn có ý nghĩa trong tên chỉ số hoặc metric_id
        name_tokens = set(name_lower.split()) | set(metric_id.split("_"))
        for word in q_norm.split():
            if len(word) >= 3 and word not in stop_words and word in name_tokens:
                score += 5

        if score > best_score:
            best_score = score
            best_metric = metric

    # Chỉ công nhận tìm thấy khi score vượt ngưỡng tin cậy (>= 10)
    if best_metric is not None and best_score >= 10:
        return {
            "found": True,
            "metric_id": best_metric.metric_id,
            "vietnamese_name": best_metric.vietnamese_name,
            "formula": best_metric.formula,
            "required_tables": best_metric.required_tables,
            "description": best_metric.description,
        }

    return {
        "found": False,
        "message": f"Không tìm thấy định nghĩa chỉ số nghiệp vụ phù hợp cho từ khóa: '{query}'.",
        "available_metrics": [
            f"{m.vietnamese_name} ({m.metric_id}): {m.formula}"
            for m in TPCH_SEMANTIC_METRICS.values()
        ],
    }


# ==============================================================================
# LANGCHAIN TOOL OBJECTS (DÙNG ĐỂ BIND_TOOLS CHO LLM AGENTS)
# ==============================================================================

search_tables_and_columns_tool = tool(search_tables_and_columns)
get_column_samples_and_values_tool = tool(get_column_samples_and_values)
find_join_path_tool = tool(find_join_path)
search_business_definition_tool = tool(search_business_definition)

# Bộ công cụ cho SQL Generator (cả 4 tools)
SQL_GENERATOR_TOOLS: list[Any] = [
    search_tables_and_columns_tool,
    get_column_samples_and_values_tool,
    find_join_path_tool,
    search_business_definition_tool,
]

# Bộ công cụ cho Direct Chat Node (tra cứu catalog/semantic không cần SQL)
DIRECT_CHAT_TOOLS: list[Any] = [
    search_tables_and_columns_tool,
    get_column_samples_and_values_tool,
    search_business_definition_tool,
]

__all__ = [
    "DIRECT_CHAT_TOOLS",
    "SQL_GENERATOR_TOOLS",
    "find_join_path",
    "find_join_path_tool",
    "get_column_samples_and_values",
    "get_column_samples_and_values_tool",
    "search_business_definition",
    "search_business_definition_tool",
    "search_tables_and_columns",
    "search_tables_and_columns_tool",
]
