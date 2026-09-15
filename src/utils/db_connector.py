import concurrent.futures
import json
import logging
import time
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger(__name__)

# Ước lượng kích thước trung bình của một ô dữ liệu trong bảng TPC-H (bytes/cell/column)
AVG_BYTES_PER_COLUMN_CELL: int = 12


class CostEstimateResult(BaseModel):
    """Kết quả ước lượng dung lượng và chi phí quét dữ liệu của câu truy vấn."""

    estimated_bytes: int = Field(description="Dung lượng dữ liệu quét ước tính (bytes)")
    estimated_rows: int | None = Field(
        default=None, description="Số dòng quét ước tính"
    )
    is_within_budget: bool = Field(
        description="True nếu chi phí quét nằm trong ngân sách cho phép"
    )
    max_budget_bytes: int = Field(
        description="Ngưỡng dung lượng tối đa được cấu hình cho người dùng"
    )
    explanation: str | None = Field(
        default=None, description="Giải thích chi tiết về ước lượng chi phí từ EXPLAIN"
    )


class QueryResult(BaseModel):
    """Kết quả thực thi câu lệnh SQL trên Database Warehouse."""

    success: bool = Field(description="True nếu câu truy vấn thực thi thành công")
    data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách các bản ghi kết quả dạng dictionary",
    )
    columns: list[str] = Field(
        default_factory=list, description="Danh sách tên các cột trong kết quả"
    )
    row_count: int = Field(default=0, description="Tổng số dòng trả về")
    execution_time_ms: float = Field(
        default=0.0, description="Thời gian thực thi truy vấn (mili-giây)"
    )
    bytes_scanned: int = Field(
        default=0, description="Dung lượng dữ liệu đã quét thực tế (bytes)"
    )
    error_message: str | None = Field(
        default=None, description="Thông báo lỗi nếu thực thi thất bại"
    )


class BaseWarehouseConnector(ABC):
    """Lớp cơ sở trừu tượng cho các kết nối Data Warehouse (Strategy Pattern)."""

    @abstractmethod
    def estimate_query_cost(
        self, sql: str, max_budget_bytes: int = 1073741824
    ) -> CostEstimateResult:
        """Ước lượng chi phí (dry-run/explain) trước khi chạy thật."""

    @abstractmethod
    def execute_query(self, sql: str, timeout_seconds: int = 30) -> QueryResult:
        """Thực thi câu truy vấn an toàn."""


class DuckDBConnector(BaseWarehouseConnector):
    """Warehouse Engine chính của dự án: Chạy DuckDB local, phân tích EXPLAIN JSON để Cost Guard."""

    def __init__(
        self,
        db_path: str | None = None,
        connection: duckdb.DuckDBPyConnection | None = None,
    ) -> None:
        self.db_path = db_path or get_settings().duckdb_path
        self._conn = connection or duckdb.connect(self.db_path)

    def estimate_query_cost(
        self,
        sql: str,
        max_budget_bytes: int = 1073741824,  # Mặc định 1GB
    ) -> CostEstimateResult:
        """Ước lượng chi phí quét dữ liệu bằng cách phân tích EXPLAIN (FORMAT JSON) của DuckDB.

        Args:
            sql: Câu lệnh SQL cần ước lượng.
            max_budget_bytes: Ngưỡng ngân sách dung lượng cho phép (bytes).

        Returns:
            CostEstimateResult: Kết quả phân tích từ execution plan của DuckDB.
        """
        total_estimated_rows = 0
        total_estimated_bytes = 0
        scanned_tables_info: list[str] = []

        try:
            # Chạy EXPLAIN (FORMAT JSON) trực tiếp trên DuckDB để lấy kế hoạch vật lý thực tế
            explain_query = f"EXPLAIN (FORMAT JSON) {sql}"
            res = self._conn.execute(explain_query).fetchall()

            if res and len(res) > 0 and len(res[0]) > 1:
                plan_json_str = res[0][1]
                plan_data = json.loads(plan_json_str)

                # Hàm đệ quy duyệt qua cây kế hoạch tìm các node SCAN
                def traverse_plan(node: dict[str, Any]) -> None:
                    nonlocal total_estimated_rows, total_estimated_bytes
                    node_name = node.get("name", "")
                    extra_info = node.get("extra_info", {})

                    if "SCAN" in node_name:
                        table_name = extra_info.get("Table", "unknown_table")
                        projections = extra_info.get("Projections", [])
                        cardinality_str = extra_info.get("Estimated Cardinality", "0")

                        try:
                            cardinality = int(cardinality_str)
                        except (ValueError, TypeError):
                            cardinality = 1000

                        num_cols = len(projections) if projections else 5
                        # Dung lượng quét ước tính = số dòng x số cột thực tế được scan x kích thước ô trung bình
                        bytes_for_scan = (
                            cardinality * num_cols * AVG_BYTES_PER_COLUMN_CELL
                        )

                        total_estimated_rows += cardinality
                        total_estimated_bytes += bytes_for_scan
                        scanned_tables_info.append(
                            f"{table_name} (~{cardinality:,} rows, {num_cols} cols)"
                        )

                    for child in node.get("children", []):
                        traverse_plan(child)

                for root_node in plan_data:
                    traverse_plan(root_node)

        except duckdb.Error as exc:
            # Nếu câu SQL có lỗi cú pháp hoặc cột không tồn tại, EXPLAIN sẽ fail
            logger.warning("DuckDB EXPLAIN failed: %s", exc)
            return CostEstimateResult(
                estimated_bytes=1024,
                estimated_rows=0,
                is_within_budget=True,
                max_budget_bytes=max_budget_bytes,
                explanation=f"Không thể chạy EXPLAIN: {exc}",
            )

        # Đảm bảo mức tối thiểu 1024 bytes nếu query hợp lệ
        total_estimated_bytes = max(total_estimated_bytes, 1024)
        is_within_budget = total_estimated_bytes <= max_budget_bytes

        explanation = (
            f"[DuckDB EXPLAIN Cost Guard] Ước lượng quét ~{total_estimated_bytes:,} bytes "
            f"(~{total_estimated_rows:,} dòng) qua các node scan: {', '.join(scanned_tables_info) or 'None'}."
            f" Ngân sách tối đa: {max_budget_bytes:,} bytes."
        )

        return CostEstimateResult(
            estimated_bytes=total_estimated_bytes,
            estimated_rows=total_estimated_rows,
            is_within_budget=is_within_budget,
            max_budget_bytes=max_budget_bytes,
            explanation=explanation,
        )

    def execute_query(
        self,
        sql: str,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        """Thực thi câu truy vấn trên DuckDB và đo đạc thời gian chạy.

        Args:
            sql: Câu lệnh SQL cần chạy.
            timeout_seconds: Thời gian tối đa cho phép chạy (giây).

        Returns:
            QueryResult: Dữ liệu bảng kết quả hoặc thông báo lỗi.
        """
        start_time = time.perf_counter()

        def _execute_sync() -> tuple[list[str], list[Any]]:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            desc = cursor.description
            cols = [d[0] for d in desc] if desc else []
            r = cursor.fetchall()
            return cols, r

        try:
            if timeout_seconds > 0:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_execute_sync)
                    try:
                        columns, rows = future.result(timeout=timeout_seconds)
                    except concurrent.futures.TimeoutError:
                        try:
                            self._conn.interrupt()
                        except Exception as int_exc:  # noqa: BLE001
                            logger.debug(
                                "Failed to interrupt DuckDB connection: %s", int_exc
                            )
                        execution_time_ms = round(
                            (time.perf_counter() - start_time) * 1000, 2
                        )
                        return QueryResult(
                            success=False,
                            execution_time_ms=execution_time_ms,
                            error_message=(
                                f"Truy vấn vượt quá thời gian tối đa cho phép ({timeout_seconds} giây)."
                            ),
                        )
            else:
                columns, rows = _execute_sync()

            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Chuyển đổi dữ liệu sang dạng JSON-serializable (date -> str, Decimal -> float)
            data: list[dict[str, Any]] = []
            for row in rows:
                row_dict: dict[str, Any] = {}
                for col_name, val in zip(columns, row):
                    if hasattr(val, "isoformat"):
                        row_dict[col_name] = val.isoformat()
                    elif isinstance(val, Decimal):
                        row_dict[col_name] = float(val)
                    else:
                        row_dict[col_name] = val
                data.append(row_dict)

            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=len(data),
                execution_time_ms=execution_time_ms,
            )
        except duckdb.Error as exc:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return QueryResult(
                success=False,
                execution_time_ms=execution_time_ms,
                error_message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return QueryResult(
                success=False,
                execution_time_ms=execution_time_ms,
                error_message=str(exc),
            )


# Singleton instance cho DuckDB Connector
_default_duckdb_connector: DuckDBConnector | None = None


def get_duckdb_connector(db_path: str | None = None) -> DuckDBConnector:
    """Singleton getter trả về DuckDBConnector kết nối tới file database cấu hình."""
    global _default_duckdb_connector
    if _default_duckdb_connector is None or db_path is not None:
        _default_duckdb_connector = DuckDBConnector(db_path=db_path)
    return _default_duckdb_connector


class BigQueryConnector(BaseWarehouseConnector):
    """Optional Adapter cho Google Cloud BigQuery (dành cho triển khai Enterprise Cloud)."""

    def __init__(
        self,
        project_id: str | None = None,
        dataset_id: str | None = None,
    ) -> None:
        self.project_id = project_id
        self.dataset_id = dataset_id

    def estimate_query_cost(
        self,
        sql: str,
        max_budget_bytes: int = 1073741824,
    ) -> CostEstimateResult:
        """Sử dụng flag dry_run=True của BigQuery API để đo chính xác total_bytes_processed."""
        try:
            from google.cloud import bigquery
        except ImportError:
            logger.warning("Thư viện google-cloud-bigquery chưa được cài đặt.")
            return CostEstimateResult(
                estimated_bytes=0,
                is_within_budget=True,
                max_budget_bytes=max_budget_bytes,
                explanation="Chưa cài đặt google-cloud-bigquery client.",
            )

        try:
            client = bigquery.Client(project=self.project_id)
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            query_job = client.query(sql, job_config=job_config)

            total_bytes = query_job.total_bytes_processed or 0
            is_within_budget = total_bytes <= max_budget_bytes

            explanation = (
                f"[BigQuery dryRun] Truy vấn này sẽ quét {total_bytes:,} bytes. "
                f"Ngân sách tối đa: {max_budget_bytes:,} bytes."
            )

            return CostEstimateResult(
                estimated_bytes=total_bytes,
                is_within_budget=is_within_budget,
                max_budget_bytes=max_budget_bytes,
                explanation=explanation,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("BigQuery dry-run error: %s", exc)
            return CostEstimateResult(
                estimated_bytes=0,
                is_within_budget=False,
                max_budget_bytes=max_budget_bytes,
                explanation=f"Lỗi khi thực hiện BigQuery dry-run: {exc}",
            )

    def execute_query(
        self,
        sql: str,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        """Thực thi câu truy vấn trên BigQuery."""
        try:
            from google.cloud import bigquery
        except ImportError:
            return QueryResult(
                success=False,
                error_message="google-cloud-bigquery chưa được cài đặt.",
            )

        start_time = time.perf_counter()
        try:
            client = bigquery.Client(project=self.project_id)
            query_job = client.query(sql, timeout=timeout_seconds)
            results = query_job.result()

            rows = [dict(row.items()) for row in results]
            columns = (
                [field.name for field in query_job.schema] if query_job.schema else []
            )
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            bytes_scanned = query_job.total_bytes_billed or 0

            return QueryResult(
                success=True,
                data=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
                bytes_scanned=bytes_scanned,
            )
        except Exception as exc:  # noqa: BLE001
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return QueryResult(
                success=False,
                execution_time_ms=execution_time_ms,
                error_message=str(exc),
            )
