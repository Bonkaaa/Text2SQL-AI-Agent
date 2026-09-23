"""Dynamic Risk-based HITL Gatekeeper Evaluator cho Enterprise Database.

Module đánh giá rủi ro truy vấn đa tiêu chí (Composite Risk Scoring):
1. Tỷ lệ dung lượng quét so với ngân sách tối đa (Budget Ratio).
2. Khối lượng dòng dữ liệu quét ước tính (Estimated Rows).
3. Kiểm tra bảng lớn (Heavy Tables) có kèm bộ lọc thời gian/phân vùng (Partition Key) không.
4. Phát hiện nguy cơ bùng nổ dữ liệu (Cartesian / Cross Join).
"""

import logging

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from src.config import Settings, get_settings
from src.models.rbac import UserContext
from src.utils.db_connector import CostEstimateResult

logger = logging.getLogger(__name__)


def has_time_filter_in_where(sql: str, time_columns: set[str]) -> bool:
    """Kiểm tra xem mệnh đề WHERE của câu SQL có chứa cột thời gian/phân vùng không."""
    if not sql or not time_columns:
        return False

    try:
        parsed = sqlglot.parse_one(sql)
        where_clause = parsed.find(exp.Where)
        if not where_clause:
            return False

        # 1. Trích xuất tất cả tên cột xuất hiện trong mệnh đề WHERE
        where_cols = {col.name.lower() for col in where_clause.find_all(exp.Column)}
        for col_name in where_cols:
            if any(tc in col_name for tc in time_columns):
                return True

        # 2. Kiểm tra nếu có biểu thức Date / Timestamp literals hoặc hàm năm/tháng
        if list(where_clause.find_all(exp.Date)) or list(
            where_clause.find_all(exp.CurrentDate)
        ):
            return True

        # 3. Kiểm tra các hàm trích xuất thời gian: EXTRACT, YEAR, DATE_PART
        for func in where_clause.find_all(exp.Anonymous):
            if func.name.lower() in ("year", "month", "date_part", "date_trunc"):
                return True

        return False

    except (SqlglotError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("Lỗi khi parse AST kiểm tra time filter, dùng regex fallback: %s", exc)
        lower_sql = sql.lower()
        where_idx = lower_sql.find("where")
        if where_idx == -1:
            return False
        where_text = lower_sql[where_idx:]
        return any(tc in where_text for tc in time_columns)


def has_cartesian_join_risk(sql: str) -> bool:
    """Phát hiện nguy cơ Cross Join hoặc Join không điều kiện làm bùng nổ dữ liệu."""
    if not sql:
        return False

    try:
        parsed = sqlglot.parse_one(sql)
        # Kiểm tra CROSS JOIN
        for join in parsed.find_all(exp.Join):
            if join.kind and "cross" in join.kind.lower():
                return True
            # Join mà không có ON hoặc USING và không phải NATURAL JOIN
            if (
                not join.args.get("on")
                and not join.args.get("using")
                and not (join.kind and "natural" in join.kind.lower())
            ):
                return True
        return False
    except (SqlglotError, ValueError, TypeError, AttributeError):
        lower_sql = sql.lower()
        return "cross join" in lower_sql


def evaluate_query_risk(
    sql: str,
    estimate: CostEstimateResult,
    tables_used: list[str],
    user_context: UserContext | None = None,
    settings: Settings | None = None,
) -> tuple[bool, str, int]:
    """Tính điểm rủi ro tổng hợp (Composite Risk Score) để quyết định kích hoạt HITL.

    Args:
        sql: Câu truy vấn SQL dự kiến chạy.
        estimate: Kết quả ước lượng chi phí từ EXPLAIN / dry-run.
        tables_used: Danh sách các bảng tham gia truy vấn.
        user_context: Thông tin vai trò & hạn mức người dùng.
        settings: Cấu hình hệ thống (nếu None sẽ lấy get_settings()).

    Returns:
        tuple[is_hitl, explanation, risk_score]:
        - is_hitl: True nếu câu truy vấn cần con người bấm duyệt.
        - explanation: Chuỗi diễn giải lý do rủi ro hiển thị cho người dùng.
        - risk_score: Điểm số rủi ro tính được (0 đến 100).
    """
    cfg = settings or get_settings()

    # Nếu tính năng HITL bị tắt trong cấu hình hệ thống
    if not cfg.hitl_enabled:
        return False, "Cơ chế HITL đang tạm tắt trong cấu hình.", 0

    risk_score = 0
    risk_factors: list[str] = []

    max_budget = (
        user_context.max_cost_bytes
        if (user_context and user_context.max_cost_bytes)
        else cfg.max_bytes_scanned
    )
    max_budget = max(max_budget, 1024)

    # --------------------------------------------------------------------------
    # 1. Tiêu chí Dung lượng quét vs Ngân sách (Budget Ratio)
    # --------------------------------------------------------------------------
    budget_ratio = estimate.estimated_bytes / max_budget
    if budget_ratio >= 0.7:
        risk_score += 45
        risk_factors.append(
            f"Dung lượng quét rất lớn ({estimate.estimated_bytes / (1024**2):.1f} MB, "
            f"chiếm {budget_ratio * 100:.0f}% ngân sách tối đa)"
        )
    elif budget_ratio >= cfg.hitl_budget_ratio_threshold:
        risk_score += 30
        risk_factors.append(
            f"Dung lượng quét vượt ngưỡng cảnh báo ({estimate.estimated_bytes / (1024**2):.1f} MB, "
            f"chiếm {budget_ratio * 100:.0f}% ngân sách)"
        )

    # --------------------------------------------------------------------------
    # 2. Tiêu chí Số lượng dòng quét ước tính (Estimated Rows Threshold)
    # --------------------------------------------------------------------------
    if estimate.estimated_rows >= cfg.hitl_rows_threshold:
        risk_score += 25
        risk_factors.append(
            f"Khối lượng quét lớn (~{estimate.estimated_rows:,} dòng, "
            f"vượt ngưỡng {cfg.hitl_rows_threshold:,} dòng)"
        )

    # --------------------------------------------------------------------------
    # 3. Tiêu chí Bảng Lớn (Heavy Tables) thiếu bộ lọc thời gian
    # --------------------------------------------------------------------------
    heavy_tables = cfg.heavy_tables_set
    clean_tables_used = {t.strip().lower() for t in tables_used if t}
    matched_heavy = heavy_tables.intersection(clean_tables_used)

    if matched_heavy:
        has_time = has_time_filter_in_where(sql, cfg.time_columns_set)
        if not has_time:
            risk_score += 35
            table_names = ", ".join(matched_heavy)
            risk_factors.append(
                f"Truy vấn trên bảng dữ liệu lớn ({table_names}) nhưng thiếu bộ lọc mốc thời gian/phân vùng"
            )

    # --------------------------------------------------------------------------
    # 4. Tiêu chí Phát hiện Cartesian Join / Cross Join
    # --------------------------------------------------------------------------
    if has_cartesian_join_risk(sql):
        risk_score += 40
        risk_factors.append("Phát hiện nguy cơ tích đề-các (Cross Join không điều kiện)")

    # --------------------------------------------------------------------------
    # 5. Quyết định kích hoạt HITL (Threshold: Điểm rủi ro >= 50)
    # --------------------------------------------------------------------------
    is_hitl = risk_score >= 50

    if is_hitl:
        explanation = (
            f"Truy vấn yêu cầu phê duyệt Human-In-The-Loop (Risk Score: {risk_score}/100). "
            f"Lý do: {'; '.join(risk_factors)}."
        )
        logger.info("[HITL Gatekeeper] Kích hoạt HITL: %s", explanation)
    else:
        explanation = f"Truy vấn an toàn (Risk Score: {risk_score}/100), cho phép thực thi tự động."

    return is_hitl, explanation, risk_score
