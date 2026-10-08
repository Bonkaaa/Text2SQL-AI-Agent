import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryInputCard } from "../QueryInputCard";

// Mock AppContext
vi.mock("@/context/AppContext", () => ({
  useAppContext: () => ({
    showToast: vi.fn(),
  }),
}));

describe("Universal Data Command Bar (Task 2.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render multiline textarea, TPC-DS mention button, và không có model dropdown / mic cũ", () => {
    render(<QueryInputCard onSubmit={vi.fn()} />);

    // Phải là textarea thay vì input 1 dòng thông thường
    const textarea = screen.getByRole("textbox");
    expect(textarea.tagName).toBe("TEXTAREA");

    // Nút chọn nhanh bảng TPC-DS trên toolbar
    expect(screen.getByRole("button", { name: /bảng tpc-ds/i })).toBeInTheDocument();

    // Không còn icon micro di động và dropdown TPC-H/Flash giả lập
    expect(screen.queryByTitle(/ghi âm/i)).toBeNull();
    expect(screen.queryByText("TPC-H")).toBeNull();
    expect(screen.queryByText("Flash")).toBeNull();
  });

  it("2. Gõ Shift + Enter không submit form mà cho phép xuống dòng", () => {
    const handleSubmit = vi.fn();
    render(<QueryInputCard onSubmit={handleSubmit} />);

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Dòng 1" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

    // Không được gọi submit khi nhấn Shift+Enter
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("3. Gõ Enter thông thường kích hoạt onSubmit và tự động xóa trắng ô nhập", () => {
    const handleSubmit = vi.fn();
    render(<QueryInputCard onSubmit={handleSubmit} />);

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Doanh thu quý 3 theo cửa hàng" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    expect(handleSubmit).toHaveBeenCalledWith("Doanh thu quý 3 theo cửa hàng");
    expect(textarea).toHaveValue("");
  });

  it("4. Bấm nút @ Bảng TPC-DS mở popover và chọn bảng store_sales chèn vào nội dung", () => {
    render(<QueryInputCard onSubmit={vi.fn()} />);

    const mentionBtn = screen.getByRole("button", { name: /bảng tpc-ds/i });
    fireEvent.click(mentionBtn);

    // Menu danh sách bảng hiện lên, tìm bảng store_sales
    const storeSalesOption = screen.getByText("store_sales");
    expect(storeSalesOption).toBeInTheDocument();

    fireEvent.click(storeSalesOption);

    // Textarea phải được chèn @store_sales
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveValue("@store_sales ");
  });

  it("5. Bấm phím tắt Ctrl+K hoặc Cmd+K tự động focus vào command bar textarea", () => {
    render(<QueryInputCard onSubmit={vi.fn()} />);

    const textarea = screen.getByRole("textbox");
    expect(document.activeElement).not.toBe(textarea);

    // Kích hoạt shortcut Cmd+K trên window
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(document.activeElement).toBe(textarea);
  });
});
