import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { HITLApprovalCard, formatBytes } from "../HITLApprovalCard";

describe("Component 3.2: HITLApprovalCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Hàm formatBytes quy đổi dung lượng chính xác sang B, KB, MB", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(null as any)).toBe("0 B");
    expect(formatBytes(512000)).toBe("500.0 KB");
    expect(formatBytes(1048576)).toBe("1.0 MB");
    expect(formatBytes(15728640)).toBe("15.0 MB");
  });

  it("2. Render đúng cảnh báo HITL, dung lượng quy đổi và khối xem trước câu lệnh SQL", () => {
    const mockSql = "SELECT * FROM lineitem WHERE l_shipdate > '1995-01-01'";
    render(
      <HITLApprovalCard
        sql={mockSql}
        estimatedBytes={15728640}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    );

    expect(
      screen.getByText(/Cảnh báo chi phí truy vấn \(HITL Required\)/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/15.0 MB/i)).toBeInTheDocument();
    expect(screen.getByText(mockSql)).toBeInTheDocument();
  });

  it("3. Bấm nút Phê duyệt & Thực thi sẽ gọi onApprove", () => {
    const handleApprove = vi.fn();
    render(
      <HITLApprovalCard
        sql="SELECT 1"
        estimatedBytes={1000000}
        onApprove={handleApprove}
        onReject={vi.fn()}
      />
    );

    const approveBtn = screen.getByRole("button", {
      name: /Phê duyệt & Thực thi/i,
    });
    fireEvent.click(approveBtn);

    expect(handleApprove).toHaveBeenCalledTimes(1);
  });

  it("4. Bấm nút Từ chối sẽ mở rộng form nhập lý do từ chối", () => {
    render(
      <HITLApprovalCard
        sql="SELECT 1"
        estimatedBytes={1000000}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    );

    const rejectBtn = screen.getByRole("button", { name: /^Từ chối$/i });
    fireEvent.click(rejectBtn);

    expect(
      screen.getByPlaceholderText(/Nhập lý do từ chối/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Xác nhận từ chối/i })
    ).toBeInTheDocument();
  });

  it("5. Nhập lý do từ chối và bấm Xác nhận gọi onReject với đúng lý do", () => {
    const handleReject = vi.fn();
    render(
      <HITLApprovalCard
        sql="SELECT 1"
        estimatedBytes={1000000}
        onApprove={vi.fn()}
        onReject={handleReject}
      />
    );

    // Bấm mở form từ chối
    fireEvent.click(screen.getByRole("button", { name: /^Từ chối$/i }));

    // Gõ lý do
    const input = screen.getByPlaceholderText(/Nhập lý do từ chối/i);
    fireEvent.change(input, {
      target: { value: "Truy vấn quá tốn tài nguyên warehouse" },
    });

    // Bấm Xác nhận từ chối
    fireEvent.click(screen.getByRole("button", { name: /Xác nhận từ chối/i }));

    expect(handleReject).toHaveBeenCalledTimes(1);
    expect(handleReject).toHaveBeenCalledWith(
      "Truy vấn quá tốn tài nguyên warehouse"
    );
  });

  it("6. Khi isSubmitting = true, các nút bấm bị vô hiệu hóa và có hiển thị loading", () => {
    const handleApprove = vi.fn();
    render(
      <HITLApprovalCard
        sql="SELECT 1"
        estimatedBytes={1000000}
        onApprove={handleApprove}
        onReject={vi.fn()}
        isSubmitting={true}
      />
    );

    const approveBtn = screen.getByRole("button", {
      name: /Phê duyệt & Thực thi/i,
    });
    expect(approveBtn).toBeDisabled();

    fireEvent.click(approveBtn);
    expect(handleApprove).not.toHaveBeenCalled();
  });
});
