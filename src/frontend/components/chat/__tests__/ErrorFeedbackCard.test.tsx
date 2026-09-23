import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import {
  ErrorFeedbackCard,
  getErrorTypeDetails,
} from "../ErrorFeedbackCard";

describe("Component 3.3: ErrorFeedbackCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render tiêu đề lỗi mặc định và thông điệp lỗi tiếng Việt", () => {
    render(
      <ErrorFeedbackCard
        errorMessage="Không thể kết nối đến cơ sở dữ liệu DuckDB"
      />
    );

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(screen.getByText("Không thể hoàn tất truy vấn")).toBeInTheDocument();
    expect(
      screen.getByText("Không thể kết nối đến cơ sở dữ liệu DuckDB")
    ).toBeInTheDocument();
  });

  it("2. Phân loại chính xác lỗi bảo mật RBAC và hiển thị giải thích thân thiện", () => {
    render(
      <ErrorFeedbackCard
        errorMessage="Permission denied for column: c_phone"
        errorType="RBAC_VIOLATION"
      />
    );

    // Kiểm tra badge và thông điệp hướng dẫn bảo mật
    expect(screen.getByText(/Chính sách bảo mật/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Bạn không có quyền truy cập trường dữ liệu nhạy cảm/i)
    ).toBeInTheDocument();
  });

  it("3. Phân loại lỗi AST_BLOCKED và TIMEOUT đúng định dạng", () => {
    const { rerender } = render(
      <ErrorFeedbackCard
        errorMessage="Statement contains DROP TABLE"
        errorType="AST_BLOCKED"
      />
    );
    expect(screen.getByText(/Chặn bởi AST Sanitizer/i)).toBeInTheDocument();

    rerender(
      <ErrorFeedbackCard
        errorMessage="Execution timed out after 30s"
        errorType="TIMEOUT"
      />
    );
    expect(screen.getByText(/Quá thời gian thực thi/i)).toBeInTheDocument();
  });

  it("4. Hiển thị badge số lần tự sửa lỗi (Self-correction retries)", () => {
    render(
      <ErrorFeedbackCard
        errorMessage="Lỗi cú pháp SQL tại dòng 1"
        retryCount={3}
        maxRetries={3}
      />
    );

    expect(
      screen.getByText(/Tự sửa lỗi: 3\/3 lần thất bại/i)
    ).toBeInTheDocument();
  });

  it("5. Bấm nút [Thử lại] kích hoạt callback onRetry", () => {
    const handleRetry = vi.fn();
    render(
      <ErrorFeedbackCard
        errorMessage="Đã xảy ra lỗi tạm thời"
        onRetry={handleRetry}
      />
    );

    const retryButton = screen.getByRole("button", { name: /Thử lại/i });
    expect(retryButton).toBeInTheDocument();

    fireEvent.click(retryButton);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it("6. Mở rộng accordion chi tiết kỹ thuật và sao chép mã lỗi vào clipboard", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    render(
      <ErrorFeedbackCard
        errorMessage="Detailed error stack: Parser Error at Token 42"
      />
    );

    // Mặc định vùng raw error chưa mở
    const toggleButton = screen.getByRole("button", {
      name: /Chi tiết kỹ thuật/i,
    });
    expect(toggleButton).toBeInTheDocument();

    // Bấm mở accordion
    fireEvent.click(toggleButton);
    expect(screen.getByText("Chi tiết lỗi từ máy chủ:")).toBeInTheDocument();
    expect(
      screen.getAllByText("Detailed error stack: Parser Error at Token 42").length
    ).toBeGreaterThanOrEqual(1);

    // Bấm nút sao chép
    const copyButton = screen.getByRole("button", { name: /Sao chép/i });
    fireEvent.click(copyButton);

    expect(writeTextMock).toHaveBeenCalledWith(
      "Detailed error stack: Parser Error at Token 42"
    );
    expect(await screen.findByText(/Đã chép/i)).toBeInTheDocument();
  });
});
