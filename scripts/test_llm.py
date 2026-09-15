import argparse
import sys
import time
from pathlib import Path

# Đảm bảo import được src khi chạy script trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_settings
from src.services.llm_service import get_chat_model

PLACEHOLDER_KEYS = {
    "sk-your-openai-key",
    "your-gemini-key",
    "your-deepseek-key",
    "your-mistral-key",
    "",
}


def mask_key(key: str | None) -> str:
    """Ẩn phần lớn ký tự của API Key để bảo mật khi in ra màn hình."""
    if not key:
        return "(chưa cấu hình)"
    if key in PLACEHOLDER_KEYS:
        return f"{key} (placeholder - chưa thay key thật)"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def test_single_model(
    provider: str,
    tier: str,
    model_name: str | None = None,
    test_prompt: str = "Say 'API key is valid!' and nothing else.",
) -> dict:
    """Kiểm tra kết nối và tính hợp lệ của API Key với một model cụ thể."""
    settings = get_settings()

    key_map = {
        "openai": settings.openai_api_key,
        "gemini": settings.gemini_api_key,
        "deepseek": settings.deepseek_api_key,
        "mistral": settings.mistral_api_key,
    }

    current_key = key_map.get(provider)
    masked = mask_key(current_key)
    model_map = {
        "openai": (settings.openai_tier1_model, settings.openai_tier2_model),
        "gemini": (settings.gemini_tier1_model, settings.gemini_tier2_model),
        "deepseek": (settings.deepseek_tier1_model, settings.deepseek_tier2_model),
        "mistral": (settings.mistral_tier1_model, settings.mistral_tier2_model),
    }
    prov_t1, prov_t2 = model_map.get(
        provider, (settings.tier1_model, settings.tier2_model)
    )
    target_model = model_name or (prov_t1 if tier == "tier1" else prov_t2)

    print(f"\n{'=' * 60}")
    print(f"[*] Đang kiểm tra: Provider = {provider.upper()} | Tier = {tier}")
    print(f"    - Model   : {target_model}")
    print(f"    - API Key : {masked}")

    result = {
        "provider": provider,
        "tier": tier,
        "model": target_model,
        "status": "FAILED",
        "latency_sec": 0.0,
        "message": "",
    }

    if not current_key or current_key.strip() in PLACEHOLDER_KEYS:
        msg = f"API Key cho '{provider}' chưa được cấu hình hoặc vẫn là giá trị placeholder trong file .env!"
        print(f"[-] THẤT BẠI: {msg}")
        result["message"] = msg
        return result

    try:
        chat_model = get_chat_model(
            tier=tier,  # type: ignore[arg-type]
            model_name=target_model,
            provider=provider,  # type: ignore[arg-type]
            temperature=0.0,
            max_tokens=64,
        )

        if chat_model is None:
            msg = f"Không thể khởi tạo chat model cho '{provider}'. Kiểm tra package provider đã cài chưa."
            print(f"[-] THẤT BẠI: {msg}")
            result["message"] = msg
            return result

        print("    - Đang gửi truy vấn kiểm tra tới API...")
        start_time = time.perf_counter()
        response = chat_model.invoke(test_prompt)
        elapsed = time.perf_counter() - start_time
        result["latency_sec"] = round(elapsed, 2)

        content = response.content
        if isinstance(content, list):
            content = " ".join(
                item if isinstance(item, str) else str(item) for item in content
            )
        clean_content = str(content).strip().replace("\n", " ")

        print(f"[+] THÀNH CÔNG! (Thời gian phản hồi: {result['latency_sec']}s)")
        print(f"    - Phản hồi từ model: \"{clean_content}\"")

        result["status"] = "SUCCESS"
        result["message"] = clean_content

    except Exception as exc:  # noqa: BLE001
        error_type = type(exc).__name__
        error_msg = str(exc)
        print(f"[-] THẤT BẠI [{error_type}]: {error_msg}")

        # Gợi ý nguyên nhân lỗi thường gặp
        hint = ""
        lowered = error_msg.lower()
        if (
            "401" in lowered
            or "unauthorized" in lowered
            or "invalid_api_key" in lowered
            or "api_key_invalid" in lowered
        ):
            hint = "-> Gợi ý: API Key KHÔNG HỢP LỆ hoặc đã hết hạn."
        elif (
            "429" in lowered
            or "quota" in lowered
            or "rate_limit" in lowered
            or "resource_exhausted" in lowered
        ):
            hint = "-> Gợi ý: Đã vượt quá Rate Limit hoặc hết hạn mức (Quota / Credits) của tài khoản."
        elif "404" in lowered or "not_found" in lowered or "model" in lowered:
            hint = f"-> Gợi ý: Tên model '{target_model}' không tồn tại hoặc tài khoản không có quyền truy cập."
        elif "connect" in lowered or "timeout" in lowered:
            hint = "-> Gợi ý: Lỗi kết nối mạng hoặc timeout đến server provider."

        if hint:
            print(f"    {hint}")

        result["message"] = f"{error_type}: {error_msg}"

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kiểm tra kết nối và tính hợp lệ của API Key LLM."
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "gemini", "deepseek", "mistral", "all"],
        default=None,
        help="Provider cần kiểm tra (mặc định lấy theo LLM_PROVIDER trong .env)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Tên model cụ thể muốn kiểm thử (bỏ qua nếu muốn test theo cấu hình tier)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Say 'API key is valid!' and nothing else.",
        help="Prompt gửi đi để kiểm tra",
    )
    parser.add_argument(
        "--tier",
        type=str,
        choices=["tier1", "tier2", "both"],
        default="both",
        help="Cấu hình tier cần kiểm tra (tier1, tier2, hoặc cả 2)",
    )
    args = parser.parse_args()

    settings = get_settings()
    selected_provider = args.provider or settings.llm_provider

    providers_to_test = (
        ["openai", "gemini", "deepseek", "mistral"]
        if selected_provider == "all"
        else [selected_provider]
    )

    tiers_to_test = ["tier1", "tier2"] if args.tier == "both" else [args.tier]

    print("\n" + "=" * 60)
    print("      KIỂM TRA TÍNH HỢP LỆ CỦA API KEY & KẾT NỐI LLM")
    print("=" * 60)
    print(f"[*] Môi trường: {settings.app_env}")
    print(f"[*] Provider mặc định (.env): {settings.llm_provider}")
    print(f"[*] Các provider sẽ test   : {', '.join(providers_to_test)}")

    all_results = []

    for prov in providers_to_test:
        if args.model:
            # Nếu người dùng truyền model cụ thể, chỉ test 1 lần với model đó
            res = test_single_model(
                provider=prov,
                tier="custom",
                model_name=args.model,
                test_prompt=args.prompt,
            )
            all_results.append(res)
        else:
            for tier_name in tiers_to_test:
                res = test_single_model(
                    provider=prov,
                    tier=tier_name,
                    test_prompt=args.prompt,
                )
                all_results.append(res)

    # Bảng tổng kết
    print(f"\n{'=' * 60}")
    print("                    BẢNG TỔNG KẾT")
    print(f"{'=' * 60}")
    print(f"{'Provider':<10} | {'Tier':<7} | {'Model':<18} | {'Status':<8} | {'Time'}")
    print("-" * 60)
    for r in all_results:
        status_str = "OK" if r["status"] == "SUCCESS" else "FAIL"
        time_str = f"{r['latency_sec']}s" if r["status"] == "SUCCESS" else "-"
        print(
            f"{r['provider']:<10} | {r['tier']:<7} | {r['model']:<18} | {status_str:<8} | {time_str}"
        )
    print("=" * 60 + "\n")

    # Exit code phản ánh kết quả
    has_failed = any(r["status"] != "SUCCESS" for r in all_results)
    if has_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
