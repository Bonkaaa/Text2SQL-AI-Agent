import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryInputCard, ChatInput } from "../QueryInputCard";

// Mock AppContext
vi.mock("@/context/AppContext", () => ({
  useAppContext: () => ({
    showToast: vi.fn(),
  }),
}));

describe("Component 2.1: QueryInputCard / ChatInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render đúng input, placeholder, model switcher và nút hành động", () => {
    render(<QueryInputCard onSubmit={vi.fn()} />);

    const input = screen.getByPlaceholderText("Ask Text2SQL...");
    expect(input).toBeInTheDocument();
    expect(screen.getByText("TPC-H")).toBeInTheDocument();
    expect(screen.getByTitle("Đính kèm tệp")).toBeInTheDocument();
  });

  it("2. Hỗ trợ placeholder tùy chỉnh qua prop", () => {
    render(
      <QueryInputCard
        onSubmit={vi.fn()}
        placeholder="Nhập câu hỏi phân tích dữ liệu..."
      />
    );

    expect(
      screen.getByPlaceholderText("Nhập câu hỏi phân tích dữ liệu...")
    ).toBeInTheDocument();
  });

  it("3. Gõ câu hỏi và nhấn Enter sẽ kích hoạt onSubmit với chuỗi đã trim và tự xóa trắng ô nhập", () => {
    const handleSubmit = vi.fn();
    render(<QueryInputCard onSubmit={handleSubmit} />);

    const input = screen.getByPlaceholderText("Ask Text2SQL...") as HTMLInputElement;
    fireEvent.change(input, {
      target: { value: "   Doanh thu theo 5 khu vực   " },
    });
    expect(input.value).toBe("   Doanh thu theo 5 khu vực   ");

    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    expect(handleSubmit).toHaveBeenCalledWith("Doanh thu theo 5 khu vực");
    expect(input.value).toBe("");
  });

  it("4. Bấm nút gửi (mũi tên) kích hoạt onSubmit khi có nội dung", () => {
    const handleSubmit = vi.fn();
    render(<QueryInputCard onSubmit={handleSubmit} />);

    const input = screen.getByPlaceholderText("Ask Text2SQL...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Top 5 khách hàng" } });

    const sendBtn = screen.getByTitle("Gửi câu hỏi");
    fireEvent.click(sendBtn);

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    expect(handleSubmit).toHaveBeenCalledWith("Top 5 khách hàng");
    expect(input.value).toBe("");
  });

  it("5. Không gọi onSubmit khi nội dung rỗng hoặc chỉ có khoảng trắng", () => {
    const handleSubmit = vi.fn();
    render(<QueryInputCard onSubmit={handleSubmit} />);

    const input = screen.getByPlaceholderText("Ask Text2SQL...");
    fireEvent.change(input, { target: { value: "    " } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("6. Khi isLoading = true, input bị disabled và nút hiển thị spinner", () => {
    const handleSubmit = vi.fn();
    render(<QueryInputCard onSubmit={handleSubmit} isLoading={true} />);

    const input = screen.getByPlaceholderText("Ask Text2SQL...");
    expect(input).toBeDisabled();

    // Thử submit khi loading
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("7. Hỗ trợ prop onSendMessage như một alias chuẩn cho onSubmit", () => {
    const handleSend = vi.fn();
    render(<ChatInput onSendMessage={handleSend} />);

    const input = screen.getByPlaceholderText("Ask Text2SQL...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Câu hỏi test alias" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(handleSend).toHaveBeenCalledTimes(1);
    expect(handleSend).toHaveBeenCalledWith("Câu hỏi test alias");
  });

  it("8. Khởi tạo với initialValue và tự động điền", () => {
    render(
      <QueryInputCard
        onSubmit={vi.fn()}
        initialValue="Giá trị khởi tạo ban đầu"
      />
    );

    const input = screen.getByPlaceholderText("Ask Text2SQL...") as HTMLInputElement;
    expect(input.value).toBe("Giá trị khởi tạo ban đầu");
  });
});
