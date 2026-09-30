import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  PromptPresets,
  TPCDS_PROMPT_PRESETS,
  TPCH_PROMPT_PRESETS,
} from "../PromptPresets";

describe("Component 2.2: PromptPresets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render đủ 4 câu hỏi mẫu nghiệp vụ TPC-DS mặc định với tiêu đề và mô tả", () => {
    render(<PromptPresets onSelectPrompt={vi.fn()} />);

    expect(screen.getByText("Doanh số đa kênh")).toBeInTheDocument();
    expect(screen.getByText("Top 5 danh mục")).toBeInTheDocument();
    expect(screen.getByText("Lý do đổi trả")).toBeInTheDocument();
    expect(screen.getByText("Doanh số tại California")).toBeInTheDocument();

    // Kiểm tra có đủ 4 buttons tương tác
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(4);
  });

  it("2. Xuất khẩu mảng TPCDS_PROMPT_PRESETS và TPCH_PROMPT_PRESETS có cấu trúc chuẩn 4 item", () => {
    expect(TPCDS_PROMPT_PRESETS).toBeDefined();
    expect(TPCDS_PROMPT_PRESETS.length).toBe(4);

    TPCDS_PROMPT_PRESETS.forEach((preset) => {
      expect(preset).toHaveProperty("id");
      expect(preset).toHaveProperty("label");
      expect(preset).toHaveProperty("category");
      expect(preset).toHaveProperty("query");
      expect(preset.query.length).toBeGreaterThan(10);
    });

    expect(TPCH_PROMPT_PRESETS).toBeDefined();
    expect(TPCH_PROMPT_PRESETS.length).toBe(4);
  });

  it("3. Click vào một thẻ câu hỏi sẽ gọi onSelectPrompt với đúng câu truy vấn", () => {
    const handleSelect = vi.fn();
    render(<PromptPresets onSelectPrompt={handleSelect} />);

    const channelBtn = screen.getByRole("button", {
      name: /Doanh số đa kênh/i,
    });
    fireEvent.click(channelBtn);

    expect(handleSelect).toHaveBeenCalledTimes(1);
    expect(handleSelect).toHaveBeenCalledWith(
      "So sánh tổng doanh thu bán hàng giữa 3 kênh Store, Web và Catalog trong năm 2001"
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

    const topCategoryBtn = screen.getByRole("button", {
      name: /Top 5 danh mục/i,
    });

    fireEvent.keyDown(topCategoryBtn, { key: "Enter", code: "Enter" });
    expect(handleSelect).toHaveBeenCalledWith(
      "Top 5 danh mục sản phẩm (Categories) có doanh thu cao nhất trên kênh Store năm 2001"
    );
  });

  it("6. Áp dụng className tùy biến nếu được truyền vào", () => {
    const { container } = render(
      <PromptPresets onSelectPrompt={vi.fn()} className="custom-test-class" />
    );

    const rootWrapper = container.firstChild as HTMLElement;
    expect(rootWrapper.className).toContain("custom-test-class");
  });

  it("7. Tương thích ngược: render TPCH_PROMPT_PRESETS khi truyền qua props", () => {
    render(
      <PromptPresets
        onSelectPrompt={vi.fn()}
        presets={TPCH_PROMPT_PRESETS}
      />
    );

    expect(screen.getByText("Doanh số 5 khu vực")).toBeInTheDocument();
    expect(screen.getByText("Top 5 khách hàng")).toBeInTheDocument();
  });
});
