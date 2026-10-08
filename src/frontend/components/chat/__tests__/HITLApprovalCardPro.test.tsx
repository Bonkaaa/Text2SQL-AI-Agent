import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { HITLApprovalCard, getRiskTier } from "../HITLApprovalCard";

describe("HITLApprovalCard Pro (Risk Tiering, Cost Gauge & Rejection Quick Chips)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. should compute correct risk tiers based on scanned bytes", () => {
    expect(getRiskTier(20 * 1024 * 1024)).toBe("low"); // 20 MB -> low
    expect(getRiskTier(150 * 1024 * 1024)).toBe("medium"); // 150 MB -> medium
    expect(getRiskTier(600 * 1024 * 1024)).toBe("high"); // 600 MB -> high
  });

  it("2. should display correct Risk Tier badge in the UI", () => {
    render(
      <HITLApprovalCard
        estimatedBytes={600 * 1024 * 1024} // 600 MB -> High
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    );

    expect(screen.getByText(/Rủi ro cao|High Risk/i)).toBeInTheDocument();
  });

  it("3. should display Cost Gauge progress bar with appropriate width", () => {
    render(
      <HITLApprovalCard
        estimatedBytes={250 * 1024 * 1024} // 250 MB
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    );

    const progressBar = screen.getByRole("progressbar");
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute("aria-valuenow");
  });

  it("4. should populate rejection reason when clicking quick suggestion chip", () => {
    const onReject = vi.fn();
    render(
      <HITLApprovalCard
        estimatedBytes={100 * 1024 * 1024}
        onApprove={vi.fn()}
        onReject={onReject}
      />
    );

    // Bấm nút Từ chối để mở form
    const rejectBtn = screen.getByRole("button", { name: /^Từ chối$/i });
    fireEvent.click(rejectBtn);

    // Tìm chip gợi ý "Thiếu điều kiện lọc thời gian"
    const quickChip = screen.getByRole("button", { name: /Thiếu điều kiện lọc/i });
    expect(quickChip).toBeInTheDocument();
    fireEvent.click(quickChip);

    // Input được điền tự động
    const input = screen.getByPlaceholderText(/Nhập lý do từ chối/i) as HTMLInputElement;
    expect(input.value).toContain("Thiếu điều kiện lọc");

    // Xác nhận từ chối
    const confirmBtn = screen.getByRole("button", { name: /Xác nhận từ chối/i });
    fireEvent.click(confirmBtn);

    expect(onReject).toHaveBeenCalledTimes(1);
    expect(onReject).toHaveBeenCalledWith(expect.stringContaining("Thiếu điều kiện lọc"));
  });
});
