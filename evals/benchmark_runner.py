"""Spider-like Benchmark Runner cho Hệ thống Text-to-SQL AI Agent (Phase 4 - Verification & Eval).

Đo lường các chỉ số cốt lõi theo tiêu chuẩn benchmark học thuật và đồ án:
1. VSR (Valid SQL Rate): Tỷ lệ câu SQL sinh ra hợp lệ và thực thi thành công trên database.
2. EX (Execution Accuracy): Tỷ lệ câu SQL sinh ra cho kết quả thực thi khớp với Ground-Truth SQL.
3. Self-Correction Rate: Tỷ lệ câu truy vấn tự sửa lỗi thành công.
4. Average Latency: Thời gian trung bình xử lý mỗi câu hỏi (ms).

Cách chạy:
    python -m evals.benchmark_runner --dataset evals/datasets/benchmark_vi.json
    python -m evals.benchmark_runner --dataset evals/datasets/benchmark_vi.json --limit 5
"""

import argparse
import asyncio
import json
import logging
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import duckdb

# Đảm bảo import được src khi chạy script trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.supervisor import arun_supervisor
from src.models.rbac import UserContext, UserRole

logger = logging.getLogger(__name__)


@dataclass
class QueryEvalResult:
    """Kết quả đánh giá cho một câu hỏi benchmark."""

    query_id: str
    question: str
    difficulty: str
    category: str
    ground_truth_sql: str
    generated_sql: str | None = None
    is_valid_sql: bool = False
    is_execution_match: bool = False
    error_message: str | None = None
    execution_time_ms: float = 0.0
    actual_rows: int = 0
    expected_rows: int = 0


@dataclass
class BenchmarkSummary:
    """Báo cáo tổng kết toàn bộ phiên benchmark."""

    total_queries: int = 0
    valid_sql_count: int = 0
    execution_match_count: int = 0
    error_count: int = 0
    vsr: float = 0.0  # Valid SQL Rate (%)
    ex: float = 0.0  # Execution Accuracy (%)
    avg_latency_ms: float = 0.0
    details: list[dict[str, Any]] = field(default_factory=list)


def normalize_value(val: Any) -> Any:
    """Chuẩn hóa giá trị để so sánh độc lập kiểu dữ liệu."""
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val):
            return "NaN"
        return round(val, 2)
    if isinstance(val, (int, str, bool)):
        return val
    return str(val)


def compare_query_results(
    actual: list[tuple[Any, ...]],
    expected: list[tuple[Any, ...]],
) -> bool:
    """So sánh kết quả thực thi của 2 câu truy vấn SQL (Execution Equivalence).

    So sánh không phân biệt thứ tự dòng nếu không có ORDER BY chặt chẽ,
    và chuẩn hóa số thực (floating point tolerance).
    """
    if len(actual) != len(expected):
        return False

    norm_actual = [tuple(normalize_value(v) for v in row) for row in actual]
    norm_expected = [tuple(normalize_value(v) for v in row) for row in expected]

    # Nếu thứ tự đã khớp hoàn toàn
    if norm_actual == norm_expected:
        return True

    # Thử so sánh dạng multiset / sorted set
    try:
        return sorted([str(r) for r in norm_actual]) == sorted(
            [str(r) for r in norm_expected]
        )
    except Exception:  # noqa: BLE001
        return False


def execute_sql(con: duckdb.DuckDBPyConnection, sql: str) -> list[tuple[Any, ...]]:
    """Thực thi an toàn một câu SQL và trả về danh sách tuples."""
    clean_sql = sql.strip().rstrip(";")
    return con.execute(clean_sql).fetchall()


async def evaluate_single_query(
    item: dict[str, Any],
    con: duckdb.DuckDBPyConnection,
    mock: bool = False,
) -> QueryEvalResult:
    """Đánh giá 1 câu hỏi benchmark duy nhất."""
    query_id = item["id"]
    question = item["question"]
    difficulty = item.get("difficulty", "MEDIUM")
    category = item.get("category", "General")
    gt_sql = item["ground_truth_sql"]

    result = QueryEvalResult(
        query_id=query_id,
        question=question,
        difficulty=difficulty,
        category=category,
        ground_truth_sql=gt_sql,
    )

    # 1. Thực thi Ground-Truth SQL
    try:
        expected_rows = execute_sql(con, gt_sql)
        result.expected_rows = len(expected_rows)
    except Exception as e:  # noqa: BLE001
        result.error_message = f"Ground truth SQL failed: {e}"
        return result

    # 2. Sinh câu lệnh SQL
    start_time = time.perf_counter()
    if mock:
        generated_sql = gt_sql
        result.execution_time_ms = 1.0
    else:
        try:
            user_ctx = UserContext(
                user_id="benchmark_runner",
                session_id=f"bench_{query_id}",
                role=UserRole.ADMIN,
            )
            sup_res = await arun_supervisor(
                question=question,
                user_context=user_ctx,
                session_id=f"bench_{query_id}",
                skip_clarification=True,
            )
            generated_sql = sup_res.get("sql")
            result.execution_time_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )
        except Exception as e:  # noqa: BLE001
            result.error_message = f"Agent generation failed: {e}"
            result.execution_time_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )
            return result

    result.generated_sql = generated_sql

    if not generated_sql:
        result.error_message = "No SQL generated by Agent"
        return result

    # 3. Đánh giá VSR & EX
    try:
        actual_rows = execute_sql(con, generated_sql)
        result.actual_rows = len(actual_rows)
        result.is_valid_sql = True  # Thực thi thành công -> VSR = True

        # So sánh kết quả thực thi -> EX
        if compare_query_results(actual_rows, expected_rows):
            result.is_execution_match = True
        else:
            result.error_message = f"Row mismatch: actual {len(actual_rows)} vs expected {len(expected_rows)}"
    except Exception as e:  # noqa: BLE001
        result.is_valid_sql = False
        result.is_execution_match = False
        result.error_message = f"SQL execution error: {e}"

    return result


async def run_benchmark(
    dataset_path: str,
    limit: int | None = None,
    output_path: str | None = None,
    db_path: str = "data/tpch.duckdb",
    mock: bool = False,
) -> BenchmarkSummary:
    """Chạy toàn bộ quy trình benchmark trên tập dataset."""
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file không tồn tại: {dataset_path}")

    dataset = json.loads(path.read_text(encoding="utf-8"))

    if limit is not None and limit > 0:
        dataset = dataset[:limit]

    total = len(dataset)
    print(f"\n🚀 BẮT ĐẦU BENCHMARK: {total} câu hỏi từ {dataset_path}")
    print(f"📦 Database: {db_path} | Mode: {'MOCK' if mock else 'REAL AGENT'}")
    print("=" * 80)

    con = duckdb.connect(db_path, read_only=True)
    summary = BenchmarkSummary(total_queries=total)
    total_latency = 0.0

    for i, item in enumerate(dataset, start=1):
        q_id = item["id"]
        q_text = item["question"]
        print(f"[{i}/{total}] Đang đánh giá {q_id}: {q_text[:50]}...", end=" ")

        eval_res = await evaluate_single_query(item, con, mock=mock)
        summary.details.append(asdict(eval_res))
        total_latency += eval_res.execution_time_ms

        if eval_res.is_valid_sql:
            summary.valid_sql_count += 1
        if eval_res.is_execution_match:
            summary.execution_match_count += 1
        if eval_res.error_message:
            summary.error_count += 1

        status_flag = (
            "✅ EX PASS"
            if eval_res.is_execution_match
            else ("⚠️ VSR ONLY" if eval_res.is_valid_sql else "❌ FAILED")
        )
        print(f"-> {status_flag} ({eval_res.execution_time_ms:.1f}ms)")

    con.close()

    summary.vsr = (
        round((summary.valid_sql_count / total) * 100, 2) if total > 0 else 0.0
    )
    summary.ex = (
        round((summary.execution_match_count / total) * 100, 2) if total > 0 else 0.0
    )
    summary.avg_latency_ms = round(total_latency / total, 2) if total > 0 else 0.0

    # In báo cáo tổng kết
    print("\n" + "=" * 80)
    print("📊 BÁO CÁO KẾT QUẢ BENCHMARK (TEXT-TO-SQL ACCURACY)")
    print("=" * 80)
    print(f"• Tổng số câu hỏi kiểm thử:        {summary.total_queries}")
    print(
        f"• Số câu SQL hợp lệ (Valid SQL):    {summary.valid_sql_count}/{summary.total_queries}"
    )
    print(f"• Valid SQL Rate (VSR):            {summary.vsr}%")
    print(
        f"• Số câu khớp kết quả (Exec Match):{summary.execution_match_count}/{summary.total_queries}"
    )
    print(f"• Execution Accuracy (EX):         {summary.ex}%")
    print(f"• Thời gian phản hồi trung bình:  {summary.avg_latency_ms} ms")
    print("=" * 80)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"💾 Đã lưu báo cáo chi tiết vào: {output_path}")

    return summary


def main() -> None:
    """CLI entrypoint cho benchmark runner."""
    parser = argparse.ArgumentParser(
        description="Text-to-SQL Accuracy & Execution Benchmark Runner"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="evals/datasets/benchmark_vi.json",
        help="Đường dẫn đến tệp dataset JSON chứa ground-truth SQL",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Giới hạn số lượng câu hỏi cần chạy (mặc định chạy toàn bộ)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Đường dẫn tệp JSON để xuất báo cáo chi tiết",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/tpch.duckdb",
        help="Đường dẫn file DuckDB database",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Chạy ở chế độ Mock kiểm thử logic đối soát Ground-Truth (không gọi LLM)",
    )

    args = parser.parse_args()

    asyncio.run(
        run_benchmark(
            dataset_path=args.dataset,
            limit=args.limit,
            output_path=args.output,
            db_path=args.db_path,
            mock=args.mock,
        )
    )


if __name__ == "__main__":
    main()
