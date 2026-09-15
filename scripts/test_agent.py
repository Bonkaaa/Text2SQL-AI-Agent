"""Script kiểm thử toàn trình Deep Agent Text-to-SQL Supervisor.

Cho phép chạy câu hỏi phân tích kinh doanh mẫu hoặc nhập câu hỏi tùy ý,
hiển thị trực quan từng giai đoạn:
1. Pre-flight Decision Gatekeeper (Làm rõ câu hỏi mơ hồ).
2. Hoạch định kế hoạch động (Supervisor Todos).
3. Tra cứu ngữ cảnh dữ liệu (Schema & Categorical Retriever).
4. Sinh câu truy vấn SQL (SQL Generator).
5. Kiểm duyệt an toàn & Thực thi (Control Pipeline: AST, RBAC, Cost, Warehouse).
6. Diễn giải & Tổng hợp kết quả kinh doanh (Synthesizer).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Đảm bảo import được src khi chạy script trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.supervisor import extract_message_text
from src.config import get_settings
from src.models.rbac import UserContext, UserRole

# Danh sách câu hỏi mẫu đa dạng cấp độ để kiểm thử
SAMPLE_QUESTIONS = [
    {
        "id": "1",
        "category": "Đơn giản (Count / Aggregation)",
        "question": "Có bao nhiêu khách hàng trong cơ sở dữ liệu?",
    },
    {
        "id": "2",
        "category": "Top-N / Doanh thu (JOIN & GROUP BY)",
        "question": "Top 5 khách hàng có tổng doanh thu lớn nhất là ai?",
    },
    {
        "id": "3",
        "category": "Lọc trạng thái & Thống kê",
        "question": "Thống kê số lượng đơn hàng theo từng trạng thái đơn hàng (order status)?",
    },
    {
        "id": "4",
        "category": "Phân tích địa lý (Multi-table JOIN)",
        "question": "Tổng doanh thu bán hàng theo từng khu vực (region)?",
    },
    {
        "id": "5",
        "category": "Câu hỏi mơ hồ (Kiểm thử Clarification Gatekeeper)",
        "question": "Cho tôi xem đơn hàng",
    },
    {
        "id": "6",
        "category": "Bảo mật RBAC (Kiểm thử chặn cột PII c_phone, c_acctbal)",
        "question": "Liệt kê số điện thoại và số dư tài khoản của 10 khách hàng đầu tiên",
    },
]


def format_table(columns: list[str], rows: list[dict], max_rows: int = 10) -> str:
    """Định dạng dữ liệu trả về dạng bảng ASCII trực quan."""
    if not columns or not rows:
        return "(Không có dữ liệu trả về)"

    # Giới hạn số dòng hiển thị
    display_rows = rows[:max_rows]
    col_widths = {c: len(c) for c in columns}

    for r in display_rows:
        for c in columns:
            val_str = str(r.get(c, ""))
            col_widths[c] = max(col_widths[c], min(len(val_str), 30))

    sep_line = "+" + "+".join("-" * (col_widths[c] + 2) for c in columns) + "+"
    header_line = (
        "| " + " | ".join(f"{c:<{col_widths[c]}}" for c in columns) + " |"
    )

    lines = [sep_line, header_line, sep_line]
    for r in display_rows:
        row_str = (
            "| "
            + " | ".join(
                f"{str(r.get(c, ''))[:30]:<{col_widths[c]}}" for c in columns
            )
            + " |"
        )
        lines.append(row_str)
    lines.append(sep_line)

    if len(rows) > max_rows:
        lines.append(f"  ... và còn {len(rows) - max_rows} dòng nữa.")

    return "\n".join(lines)


def execute_test(
    question: str,
    provider: str | None = None,
    role: str = "analyst",
    skip_clarification: bool = False,
    output_json_path: str | Path | None = None,
    session_id: str | None = None,
) -> dict:
    """Thực thi câu hỏi qua Deep Agent Supervisor và in kết quả chi tiết."""
    settings = get_settings()

    # Kiểm tra database DuckDB
    db_path = Path(settings.duckdb_path)
    if not db_path.exists():
        print(f"\n[!] CẢNH BÁO: Chưa tìm thấy file DuckDB tại '{db_path}'.")
        print("    Vui lòng chạy lệnh sau để khởi tạo dữ liệu TPC-H:")
        print("    python scripts/init_db.py\n")

    # Xác định vai trò RBAC
    role_mapping = {
        "admin": UserRole.ADMIN,
        "analyst": UserRole.ANALYST,
    }
    user_role = role_mapping.get(role.lower(), UserRole.ANALYST)
    active_session_id = session_id or f"cli_{int(time.time())}"
    user_context = UserContext(
        user_id="test_user_cli",
        session_id=active_session_id,
        role=user_role,
    )

    active_provider = provider or settings.llm_provider

    print("\n" + "=" * 70)
    print("           KIỂM THỬ DEEP AGENT SUPERVISOR (TEXT-TO-SQL)")
    print("=" * 70)
    print(f"[*] Câu hỏi       : \"{question}\"")
    print(f"[*] Vai trò người : {user_role.value.upper()}")
    print(f"[*] LLM Provider  : {active_provider.upper()}")
    print(f"[*] Tier 1 Model  : {settings.tier1_model}")
    print(f"[*] Tier 2 Model  : {settings.tier2_model}")
    print(f"[*] Session ID    : {user_context.session_id}")
    print("=" * 70)
    print("[*] Đang gửi yêu cầu vào Deep Agent Supervisor...")

    start_time = time.perf_counter()

    from src.agents.supervisor import run_supervisor

    result = run_supervisor(
        question=question,
        user_context=user_context,
        session_id=user_context.session_id,
        skip_clarification=skip_clarification,
    )

    elapsed = round(time.perf_counter() - start_time, 2)
    status = result.get("status", "UNKNOWN")

    print(f"\n[*] Thời gian hoàn thành: {elapsed}s | Trạng thái: {status}")
    print("-" * 70)

    # 1. Trường hợp cần làm rõ (Clarification Required)
    if status == "CLARIFICATION_REQUIRED":
        print("\n[?] PRE-FLIGHT GATEKEEPER: CÂU HỎI CẦN LÀM RÕ (FAST-PATH)")
        print(f"    - Lý do: {result.get('ambiguity_type')}")
        print(f"    - Câu hỏi làm rõ: {result.get('clarification_question')}")
        options = result.get("suggested_options", [])
        if options:
            print("    - Các gợi ý lựa chọn:")
            for idx, opt in enumerate(options, 1):
                print(f"      {idx}. {opt}")

    # 2. Trường hợp thành công (Completed)
    elif status == "COMPLETED":
        print("\n[+] HOÀN TẤT THỰC THI (COMPLETED)")

        # Hiển thị các file sinh ra trong Virtual Filesystem
        files = result.get("files", {})
        if files:
            print("\n--- [1] VIRTUAL FILESYSTEM ARTIFACTS ---")
            for fname, fcontent in files.items():
                print(f"\n* File: {fname}")
                if fname.endswith(".sql"):
                    print("```sql")
                    print(str(fcontent).strip())
                    print("```")
                elif fname.endswith((".json", ".md")):
                    content_preview = str(fcontent)[:500]
                    print(content_preview + ("..." if len(str(fcontent)) > 500 else ""))

        # Hiển thị câu trả lời tổng hợp cuối cùng
        final_answer = extract_message_text(result.get("final_answer", ""))
        if final_answer:
            print("\n--- [2] PHẢN HỒI KINH DOANH TỔNG HỢP (SYNTHESIZED INSIGHT) ---")
            print(final_answer)

    # 3. Trường hợp truy vấn thất bại (Execution Failed)
    elif status == "EXECUTION_FAILED":
        print("\n[!] TRUY VẤN DỮ LIỆU THẤT BẠI (EXECUTION FAILED)")
        if result.get("error"):
            print(f"    - Chi tiết kỹ thuật: {result.get('error')}")
        final_answer = extract_message_text(result.get("final_answer", ""))
        if final_answer:
            print("\n--- PHẢN HỒI AN TOÀN TỪ HỆ THỐNG ---")
            print(final_answer)

    # 4. Trường hợp lỗi hệ thống (Error)
    elif status == "ERROR":
        print(f"\n[-] THẤT BẠI: {result.get('error')}")

    # 4. Lưu toàn bộ Output của Agent ra file JSON
    serialized_messages = []
    for msg in result.get("messages", []):
        msg_type = getattr(msg, "type", type(msg).__name__)
        raw_c = getattr(msg, "content", str(msg))
        entry = {
            "type": msg_type,
            "content": extract_message_text(raw_c) if isinstance(raw_c, list) else raw_c,
        }
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            entry["tool_calls"] = msg.tool_calls
        if hasattr(msg, "name") and msg.name:
            entry["name"] = msg.name
        serialized_messages.append(entry)

    final_payload = {
        "session_id": user_context.session_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "user_role": user_role.value,
        "provider": active_provider,
        "tier1_model": settings.tier1_model,
        "tier2_model": settings.tier2_model,
        "status": status,
        "execution_time_seconds": elapsed,
        "final_answer": extract_message_text(result.get("final_answer")),
        "is_ambiguous": result.get("is_ambiguous", False),
        "clarification": {
            "question": result.get("clarification_question"),
            "options": result.get("suggested_options", []),
            "reason": result.get("ambiguity_type"),
        }
        if status == "CLARIFICATION_REQUIRED"
        else None,
        "files": result.get("files", {}),
        "error": result.get("error"),
        "messages": serialized_messages,
    }

    tracer = result.get("tracer")
    trace_dir = tracer.get_trace_dir() if tracer else None
    if tracer:
        tracer.log_artifact("final_agent_output.json", final_payload)

    dest_path = (
        Path(output_json_path)
        if output_json_path
        else Path("outputs/latest_agent_output.json")
    )
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(
            json.dumps(final_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[-] Không thể ghi file JSON kết quả: {exc}")

    print("\n" + "=" * 70)
    if trace_dir:
        print(f"[*] Thư mục traces phiên    : {trace_dir}")
        print(f"[*] File JSON trace phiên   : {trace_dir / 'final_agent_output.json'}")
    print(f"[*] File JSON output mới nhất: {dest_path.resolve()}")
    print("=" * 70 + "\n")

    return {
        "question": question,
        "status": status,
        "elapsed": elapsed,
        "error": result.get("error"),
        "output_file": str(dest_path.resolve()),
    }


def interactive_chat_session(
    provider: str | None = None,
    role: str = "analyst",
    skip_clarification: bool = False,
) -> None:
    """Phiên chat tương tác nhiều lượt (Multi-turn Chat REPL) duy trì context qua Checkpointer."""
    session_id = f"cli_chat_{int(time.time())}"
    print("\n" + "=" * 70)
    print(f"       PHIÊN HỘI THOẠI ĐA LƯỢT (SESSION ID: {session_id})")
    print("=" * 70)
    print("  Gõ câu hỏi để trò chuyện với Agent (Agent sẽ ghi nhớ ngữ cảnh).")
    print("  Nhập 'exit' hoặc 'quit' để thoát phiên.")
    print("=" * 70 + "\n")

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nThoát phiên hội thoại.")
            break

        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Kết thúc phiên hội thoại.")
            break

        execute_test(
            question=user_input,
            provider=provider,
            role=role,
            skip_clarification=skip_clarification,
            session_id=session_id,
        )
        print("\n" + "-" * 70 + "\n")


def interactive_menu(provider: str | None, role: str) -> None:
    """Hiển thị menu tương tác cho người dùng chọn hoặc gõ câu hỏi."""
    while True:
        print("\n" + "=" * 60)
        print("          MENU KIỂM THỬ TEXT-TO-SQL AI AGENT")
        print("=" * 60)
        for item in SAMPLE_QUESTIONS:
            print(f"  [{item['id']}] ({item['category']})")
            print(f"      \"{item['question']}\"")
        print("  [7] Nhập câu hỏi đơn lẻ tùy ý")
        print("  [8] Bắt đầu phiên chat tương tác nhiều lượt (Multi-turn Chat)")
        print("  [0] Thoát chương trình")
        print("=" * 60)

        choice = input("\nChọn câu hỏi (0-8): ").strip()
        if choice == "0":
            print("\nTạm biệt!")
            break

        if choice == "8":
            interactive_chat_session(provider=provider, role=role)
            continue

        selected_q = None
        for item in SAMPLE_QUESTIONS:
            if item["id"] == choice:
                selected_q = item["question"]
                break

        if choice == "7":
            selected_q = input("\nNhập câu hỏi phân tích của bạn: ").strip()
            if not selected_q:
                print("[-] Câu hỏi không được để trống!")
                continue

        if not selected_q:
            print("[-] Lựa chọn không hợp lệ, vui lòng chọn từ 0 đến 8.")
            continue

        execute_test(
            question=selected_q,
            provider=provider,
            role=role,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kiểm thử toàn trình AI Agent Text-to-SQL Supervisor."
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Khởi chạy phiên hội thoại tương tác nhiều lượt (Multi-turn Chat REPL) lưu trữ context",
    )
    parser.add_argument(
        "-q",
        "--question",
        type=str,
        default=None,
        help="Câu hỏi phân tích cụ thể cần kiểm thử",
    )
    parser.add_argument(
        "-n",
        "--num-questions",
        "--count",
        type=int,
        default=None,
        help="Số lượng câu hỏi mẫu muốn tự động chạy (ví dụ: -n 1 để chỉ chạy đúng 1 câu)",
    )
    parser.add_argument(
        "-s",
        "--sample-id",
        type=str,
        default=None,
        help="Chạy cụ thể một câu hỏi mẫu theo ID (từ 1 đến 6)",
    )
    parser.add_argument(
        "-p",
        "--provider",
        type=str,
        choices=["openai", "gemini", "deepseek", "mistral"],
        default=None,
        help="Ghi đè provider (mặc định lấy theo cấu hình LLM_PROVIDER trong .env)",
    )
    parser.add_argument(
        "-r",
        "--role",
        type=str,
        choices=["analyst", "admin"],
        default="analyst",
        help="Vai trò người dùng kiểm thử RBAC (mặc định: analyst)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Đường dẫn file JSON tùy chọn để ghi output cuối cùng (mặc định: outputs/latest_agent_output.json)",
    )
    parser.add_argument(
        "--skip-clarification",
        action="store_true",
        help="Bỏ qua bước kiểm tra làm rõ câu hỏi mơ hồ (Pre-flight Gatekeeper)",
    )
    args = parser.parse_args()

    # Nếu người dùng chỉ định provider qua CLI, cập nhật vào env và reset settings cache
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
        get_settings.cache_clear()

    # Tự động chuyển provider sang gemini nếu provider hiện tại là openai nhưng chưa có key
    current_settings = get_settings()
    if (
        current_settings.llm_provider == "openai"
        and (
            not current_settings.openai_api_key
            or current_settings.openai_api_key.startswith("sk-your-openai")
        )
        and current_settings.gemini_api_key
        and not current_settings.gemini_api_key.startswith("your-gemini")
    ):
        print("[*] Phát hiện GEMINI_API_KEY đã được cấu hình trong khi OPENAI_API_KEY để trống.")
        print("[*] Tự động chuyển provider mặc định sang GEMINI cho phiên chạy này.")
        os.environ["LLM_PROVIDER"] = "gemini"
        get_settings.cache_clear()

    if args.interactive:
        interactive_chat_session(
            provider=args.provider,
            role=args.role,
            skip_clarification=args.skip_clarification,
        )
    elif args.question:
        execute_test(
            question=args.question,
            provider=args.provider,
            role=args.role,
            skip_clarification=args.skip_clarification,
            output_json_path=args.output,
        )
    elif args.sample_id:
        target = next(
            (item for item in SAMPLE_QUESTIONS if item["id"] == str(args.sample_id)),
            None,
        )
        if not target:
            print(
                f"[-] Không tìm thấy câu hỏi mẫu có ID '{args.sample_id}'. Vui lòng chọn từ 1 đến {len(SAMPLE_QUESTIONS)}."
            )
            sys.exit(1)
        execute_test(
            question=target["question"],
            provider=args.provider,
            role=args.role,
            skip_clarification=args.skip_clarification,
            output_json_path=args.output,
        )
    elif args.num_questions is not None:
        count = max(1, min(args.num_questions, len(SAMPLE_QUESTIONS)))
        selected_samples = SAMPLE_QUESTIONS[:count]
        print(f"\n[*] Bắt đầu chạy tự động {count} câu hỏi mẫu:")
        for idx, sample in enumerate(selected_samples, 1):
            print(f"    {idx}. [{sample['id']}] {sample['question']}")

        summaries = []
        for idx, sample in enumerate(selected_samples, 1):
            custom_out = args.output
            if custom_out and count > 1:
                p = Path(custom_out)
                custom_out = str(p.parent / f"{p.stem}_{idx}{p.suffix}")
            res = execute_test(
                question=sample["question"],
                provider=args.provider,
                role=args.role,
                skip_clarification=args.skip_clarification,
                output_json_path=custom_out,
            )
            summaries.append(res)

        if len(summaries) > 1:
            print("\n" + "=" * 70)
            print("                 BẢNG TỔNG HỢP KIỂM THỬ")
            print("=" * 70)
            print(f"{'ID':<4} | {'Trạng thái':<22} | {'Thời gian':<10} | {'Câu hỏi'}")
            print("-" * 70)
            for idx, s in enumerate(summaries, 1):
                q_short = s["question"][:32] + ("..." if len(s["question"]) > 32 else "")
                print(f"{idx:<4} | {s['status']:<22} | {s['elapsed']}s | {q_short}")
            print("=" * 70 + "\n")
    else:
        interactive_menu(provider=args.provider, role=args.role)


if __name__ == "__main__":
    main()
