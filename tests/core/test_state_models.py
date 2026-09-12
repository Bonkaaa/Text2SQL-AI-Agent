import pytest
from pydantic import ValidationError

from src.models.rbac import (
    UserContext,
    UserRole,
    get_role_permissions,
)
from src.models.state import (
    AgentState,
    ClarificationResult,
    RechartsConfig,
    SelfCorrectionResult,
    SQLGenerationResult,
)


def test_user_role_enum_values():
    """Kiểm tra các giá trị Enum UserRole chuẩn hóa."""
    assert UserRole.ANALYST == "Analyst"
    assert UserRole.ADMIN == "Admin"
    assert UserRole("Analyst") == UserRole.ANALYST
    assert UserRole("Admin") == UserRole.ADMIN

    with pytest.raises(ValueError):
        UserRole("Guest")


def test_user_context_defaults():
    """Kiểm tra khởi tạo UserContext với các giá trị mặc định."""
    context = UserContext(user_id="user_123", session_id="sess_abc")

    assert context.user_id == "user_123"
    assert context.session_id == "sess_abc"
    assert context.role == UserRole.ANALYST
    assert context.max_cost_bytes > 0
    assert "customer" in context.allowed_tables
    assert "c_phone" in context.denied_columns

    # Kiểm tra UserContext với quyền tùy chỉnh (custom override)
    custom_context = UserContext(
        user_id="user_456",
        session_id="sess_custom",
        role=UserRole.ANALYST,
        allowed_tables={"orders"},
        denied_columns={"o_totalprice"},
    )
    assert custom_context.allowed_tables == {"orders"}
    assert custom_context.denied_columns == {"o_totalprice"}


def test_role_permissions_analyst():
    """Kiểm tra quyền hạn của Role Analyst: bị cấm các cột PII/tài chính cá nhân."""
    allowed_tables, denied_columns = get_role_permissions(UserRole.ANALYST)

    assert "customer" in allowed_tables
    assert "orders" in allowed_tables
    assert "audit_log" not in allowed_tables  # Cấm truy cập audit log nội bộ

    # Cấm các cột PII và số dư tài khoản
    assert "c_phone" in denied_columns
    assert "c_acctbal" in denied_columns
    assert "s_phone" in denied_columns
    assert "s_acctbal" in denied_columns


def test_role_permissions_admin():
    """Kiểm tra quyền hạn của Role Admin: toàn quyền truy cập."""
    allowed_tables, denied_columns = get_role_permissions(UserRole.ADMIN)

    assert "audit_log" in allowed_tables
    assert len(denied_columns) == 0  # Admin không bị cấm cột nào


def test_clarification_result_model():
    """Kiểm tra schema ClarificationResult khi câu hỏi mơ hồ và khi rõ ràng."""
    ambiguous = ClarificationResult(
        needs_clarification=True,
        reason="Thiếu mốc thời gian cụ thể",
        clarification_question="Bạn muốn xem doanh thu năm nào?",
        suggested_options=["Năm 1995", "Năm 1996", "Tất cả các năm"],
    )
    assert ambiguous.needs_clarification is True
    assert len(ambiguous.suggested_options) == 3

    clear = ClarificationResult(needs_clarification=False)
    assert clear.needs_clarification is False
    assert len(clear.suggested_options) == 0


def test_recharts_config_model():
    """Kiểm tra validation RechartsConfig cho hiển thị trực quan."""
    chart = RechartsConfig(
        chart_type="bar",
        title="Top 5 khách hàng theo doanh thu",
        x_axis="customer_name",
        y_axis="total_revenue",
        description="Biểu đồ cột so sánh doanh thu",
    )
    assert chart.chart_type == "bar"
    assert chart.x_axis == "customer_name"

    # Sai chart_type ngoài danh sách cho phép phải raise ValidationError
    with pytest.raises(ValidationError):
        RechartsConfig(
            chart_type="scatter_3d",  # Loại chart không hỗ trợ
            title="Invalid",
            x_axis="x",
            y_axis="y",
        )


def test_agent_state_dict_structure():
    """Kiểm tra cấu trúc TypedDict của AgentState."""
    state: AgentState = {
        "session_id": "session_001",
        "question": "Doanh thu năm 1995 theo từng khu vực?",
        "retry_count": 0,
        "needs_clarification": False,
    }
    assert state["session_id"] == "session_001"
    assert state["retry_count"] == 0


def test_phase3_state_models():
    """Kiểm tra SQLGenerationResult và SelfCorrectionResult."""
    sql_res = SQLGenerationResult(
        sql="SELECT 1;",
        explanation="Test query",
    )
    assert sql_res.sql == "SELECT 1;"
    assert sql_res.dialect == "duckdb"

    sc_res = SelfCorrectionResult(
        success=True,
        sql="SELECT 1;",
        retry_count=0,
    )
    assert sc_res.success is True
    assert sc_res.retry_count == 0
