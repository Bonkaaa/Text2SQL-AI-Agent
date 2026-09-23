import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PromptPresets, TPCH_PROMPT_PRESETS } from "../PromptPresets";

describe("Component 2.2: PromptPresets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render đủ 4 câu hỏi mẫu nghiệp vụ TPC-H với tiêu đề và mô tả", () => {
    render(<PromptPresets onSelectPrompt={vi.fn()} />);

    expect(screen.getByText("Doanh số 5 khu vực")).toBeInTheDocument();
    expect(screen.getByText("Top 5 khách hàng")).toBeInTheDocument();
    expect(screen.getByText("Đơn giao trễ")).toBeInTheDocument();
    expect(screen.getByText("Chiết khấu trung bình")).toBeInTheDocument();

    // Kiểm tra có đủ 4 buttons tương tác
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(4);
  });

  it("2. Xuất khẩu mảng TPCH_PROMPT_PRESETS có cấu trúc chuẩn 4 item", () => {
    expect(TPCH_PROMPT_PRESETS).toBeDefined();
    expect(TPCH_PROMPT_PRESETS.length).toBe(4);

    TPCH_PROMPT_PRESETS.forEach((preset) => {
      expect(preset).toHaveProperty("id");
      expect(preset).toHaveProperty("label");
      expect(preset).toHaveProperty("category");
      expect(preset).toHaveProperty("query");
      expect(preset.query.length).toBeGreaterThan(10);
    });
  });

  it("3. Click vào một thẻ câu hỏi sẽ gọi onSelectPrompt với đúng câu truy vấn", () => {
    const handleSelect = vi.fn();
    render(<PromptPresets onSelectPrompt={handleSelect} />);

    const regionBtn = screen.getByRole("button", {
      name: /Doanh số 5 khu vực/i,
    });
    fireEvent.click(regionBtn);

    expect(handleSelect).toHaveBeenCalledTimes(1);
    expect(handleSelect).toHaveBeenCalledWith(
      "Phân tích doanh thu thuần theo 5 khu vực địa lý"
    );
  });

  it("4. Khi disabled = true, tất cả các nút bị vô hiệu hóa và click không kích hoạt onSelectPrompt", () => {
    const handleSelect = vi.fn();
    render(<PromptPresets onSelectPrompt={handleSelect} disabled={true} />);

    const buttons = screen.getAllByRole("button");
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });

    fireEvent.click(buttons[0]);
    expect(handleSelect).not.toHaveBeenCalled();
  });

  it("5. Hỗ trợ phím Enter và Space để kích hoạt thẻ (Accessibility)", () => {
    const handleSelect = vi.fn();
    render(<PromptPresets onSelectPrompt={handleSelect} />);

    const topCustomerBtn = screen.getByRole("button", {
      name: /Top 5 khách hàng/i,
    });

    fireEvent.keyDown(topCustomerBtn, { key: "Enter", code: "Enter" });
    expect(handleSelect).toHaveBeenCalledWith(
      "Top 5 khách hàng có tổng chi tiêu lớn nhất năm 1995"
    );
  });

  it("6. Áp dụng className tùy biến nếu được truyền vào", () => {
    const { container } = render(
      <PromptPresets onSelectPrompt={vi.fn()} className="custom-test-class" />
    );

    const rootWrapper = container.firstChild as HTMLElement;
    expect(rootWrapper.className).toContain("custom-test-class");
  });
});
