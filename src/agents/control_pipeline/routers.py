from src.models.state import ControlState


def route_after_ast(state: ControlState) -> str:
    """Định tuyến sau bước kiểm tra AST: Sang RBAC nếu hợp lệ, sang ERR nếu vi phạm."""
    if state.get("ast_valid", False):
        return "rbac_check"
    return "err_node"


def route_after_rbac(state: ControlState) -> str:
    """Định tuyến sau bước kiểm tra RBAC: Sang Cost Guard nếu hợp lệ, sang ERR nếu vi phạm."""
    if state.get("rbac_valid", False):
        return "cost_guard"
    return "err_node"


def route_after_cost(state: ControlState) -> str:
    """Định tuyến sau bước ước lượng chi phí."""
    if not state.get("cost_valid", False):
        return "err_node"

    if state.get("hitl_required", False):
        return "hitl_gate"

    return "execute"


def route_after_hitl(state: ControlState) -> str:
    """Định tuyến sau bước phê duyệt HITL: Tiếp tục execute nếu duyệt, sang ERR nếu từ chối."""
    if state.get("hitl_approved", False):
        return "execute"
    return "err_node"


def route_after_execute(state: ControlState) -> str:
    """Định tuyến sau bước thực thi: Sang Audit nếu thành công, sang ERR nếu DB lỗi/timeout."""
    execution_result = state.get("execution_result")
    if execution_result and execution_result.get("is_valid", False):
        return "audit"
    return "err_node"
