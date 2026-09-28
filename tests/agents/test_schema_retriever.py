"""Unit tests for Component 2.3: Subagent Schema & Value Retriever.

Tuân thủ quy trình TDD:
- Kiểm tra Pydantic SchemaContextResult.
- Kiểm tra tool search_tables_and_columns.
- Kiểm tra tool search_categorical_values.
- Kiểm tra hàm retrieve_schema_context tổng hợp ngữ cảnh.
- Kiểm tra cấu hình DeepAgents SubAgent dictionary (name, mode, tools, model, response_format).
"""

from src.agents.schema_retriever import (
    SCHEMA_RETRIEVER_SYSTEM_PROMPT,
    get_schema_retriever_subagent,
    retrieve_schema_context,
    schema_retriever_subagent,
    search_categorical_values,
    search_tables_and_columns,
)
from src.models.state import SchemaContextResult


class TestSchemaContextResultModel:
    """Kiểm tra tính toàn vẹn của Pydantic model SchemaContextResult."""

    def test_schema_context_result_valid_creation(self) -> None:
        result = SchemaContextResult(
            selected_tables=["customer", "orders", "lineitem"],
            join_conditions=["orders.o_custkey = customer.c_custkey"],
            categorical_filters={"c_mktsegment": "AUTOMOBILE", "r_name": "ASIA"},
            metric_formulas=["SUM(l_extendedprice * (1 - l_discount))"],
            context_markdown="### DDL Context Markdown",
        )
        assert len(result.selected_tables) == 3
        assert "customer" in result.selected_tables
        assert result.categorical_filters["c_mktsegment"] == "AUTOMOBILE"
        assert result.categorical_filters["r_name"] == "ASIA"
        assert len(result.join_conditions) == 1
        assert "DDL Context" in result.context_markdown

    def test_schema_context_result_default_factory(self) -> None:
        """Đảm bảo các trường danh sách và dict có default factory hợp lệ."""
        result = SchemaContextResult(context_markdown="Minimal Markdown")
        assert result.selected_tables == []
        assert result.join_conditions == []
        assert result.categorical_filters == {}
        assert result.metric_formulas == []
        assert result.context_markdown == "Minimal Markdown"


class TestSchemaRetrieverTools:
    """Kiểm tra các công cụ (tools) được cấp cho Schema Retriever subagent."""

    def test_search_tables_and_columns_customer_orders(self) -> None:
        """Tìm kiếm bảng liên quan đến khách hàng và đơn hàng."""
        results = search_tables_and_columns("tìm thông tin khách hàng và đơn đặt hàng")
        assert isinstance(results, list)
        assert len(results) > 0
        found_tables = [r["table"] for r in results]
        assert "customer" in found_tables or "orders" in found_tables

    def test_search_tables_and_columns_item_store(self) -> None:
        """Tìm kiếm bảng liên quan đến sản phẩm và cửa hàng."""
        results = search_tables_and_columns("giá bán sản phẩm tại cửa hàng")
        found_tables = [r["table"] for r in results]
        assert (
            "item" in found_tables
            or "store" in found_tables
            or "store_sales" in found_tables
        )

    def test_search_tables_and_columns_top_k_limit(self) -> None:
        """Giới hạn top_k bảng trả về."""
        results = search_tables_and_columns("báo cáo kinh doanh toàn bộ", top_k=3)
        assert len(results) <= 3

    def test_search_categorical_values_matching(self) -> None:
        """Tìm kiếm giá trị phân loại danh mục trong câu hỏi TPC-DS."""
        results = search_categorical_values(
            "khách hàng mua đồ gia dụng tại bang california"
        )
        assert isinstance(results, list)
        assert len(results) >= 2

        matched_values = {r["column"]: r["value"] for r in results}
        assert matched_values.get("i_category") == "Home"
        assert matched_values.get("ca_state") == "CA"

    def test_search_categorical_values_no_match(self) -> None:
        """Không tìm thấy danh mục nếu câu hỏi không chứa từ khóa phân loại."""
        results = search_categorical_values("đếm số lượng bản ghi bảng")
        assert isinstance(results, list)
        assert len(results) == 0


class TestRetrieveSchemaContext:
    """Kiểm tra hàm tổng hợp ngữ cảnh schema context."""

    def test_retrieve_schema_context_tpcds_omnichannel(self) -> None:
        """Tổng hợp đầy đủ schema cho câu hỏi nghiệp vụ bán lẻ TPC-DS kèm date_dim."""
        question = "Thống kê doanh số bán lẻ đồ gia dụng của khách hàng nam giới tại bang California năm 2001"
        result = retrieve_schema_context(question)

        assert isinstance(result, SchemaContextResult)
        # Bắt buộc phát hiện được các bảng Fact và Dimension cốt lõi
        assert "store_sales" in result.selected_tables
        assert "date_dim" in result.selected_tables  # Nhờ Time Heuristic
        assert "item" in result.selected_tables
        assert "customer" in result.selected_tables
        assert (
            "customer_address" in result.selected_tables
        )  # Nhờ Snowflake Bridge Integrity

        # Bắt buộc phát hiện được categorical values
        assert result.categorical_filters.get("i_category") == "Home"
        assert result.categorical_filters.get("cd_gender") == "M"
        assert result.categorical_filters.get("ca_state") == "CA"

        # Bắt buộc có join conditions giữa các bảng liên quan
        assert len(result.join_conditions) > 0

        # Bắt buộc có công thức doanh thu bán lẻ
        assert any(
            "ss_net_paid" in f or "ss_ext_sales_price" in f
            for f in result.metric_formulas
        )

        # Context markdown đầy đủ DDL và categorical context
        assert "### NGỮ CẢNH LƯỢC ĐỒ CƠ SỞ DỮ LIỆU" in result.context_markdown
        assert "Home" in result.context_markdown

    def test_retrieve_schema_context_explicit_tables(self) -> None:
        """Tổng hợp ngữ cảnh khi người dùng hoặc agent chỉ định trước bảng."""
        result = retrieve_schema_context(
            question="Xem thông tin sản phẩm",
            selected_tables=["item", "store_sales"],
        )
        assert "item" in result.selected_tables
        assert "store_sales" in result.selected_tables
        assert "customer" not in result.selected_tables


class TestSubagentDictionarySpec:
    """Kiểm tra thông số cấu hình SubAgent Dictionary theo chuẩn DeepAgents."""

    def test_subagent_dict_structure(self) -> None:
        subagent = schema_retriever_subagent
        assert isinstance(subagent, dict)
        assert subagent["name"] == "schema-retriever"
        assert subagent["mode"] == "isolated"
        assert "Chuyên tra cứu" in subagent["description"]
        assert subagent["system_prompt"] == SCHEMA_RETRIEVER_SYSTEM_PROMPT
        assert subagent["response_format"] == SchemaContextResult

        # Tools phải bao gồm cả 2 tools chuyên biệt
        tool_names = [t.__name__ for t in subagent["tools"]]
        assert "search_tables_and_columns" in tool_names
        assert "search_categorical_values" in tool_names

    def test_get_schema_retriever_subagent_custom_model(self) -> None:
        """Kiểm tra khởi tạo subagent dict với model override."""
        custom_subagent = get_schema_retriever_subagent(model="gemini-2.5-flash")
        assert custom_subagent["model"] == "gemini-2.5-flash"
        assert custom_subagent["mode"] == "isolated"
        assert custom_subagent["response_format"] == SchemaContextResult
