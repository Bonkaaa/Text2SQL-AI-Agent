import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ClarificationCard } from "../ClarificationCard";

describe("Component 3.1: ClarificationCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render đúng tiêu đề làm rõ câu hỏi và nội dung câu hỏi làm rõ", () => {
    render(
      <ClarificationCard
        question="Bạn muốn xem doanh thu theo 5 khu vực hay theo từng năm?"
        options={["Theo 5 khu vực", "Theo từng năm"]}
        onSelectOption={vi.fn()}
      />
    );

    expect(screen.getByText(/Cần làm rõ ý định câu hỏi/i)).toBeInTheDocument();
    expect(
      screen.getByText(
        "Bạn muốn xem doanh thu theo 5 khu vực hay theo từng năm?"
      )
    ).toBeInTheDocument();
  });

  it("2. Render danh sách các tùy chọn gợi ý dưới dạng nút chip có tiền tố A, B, C", () => {
    const mockOptions = [
      "Theo 5 khu vực địa lý",
      "Theo từng năm (1992 - 1998)",
      "Theo phân khúc khách hàng",
    ];

    render(
      <ClarificationCard
        question="Vui lòng chọn tiêu chí lọc:"
        options={mockOptions}
        onSelectOption={vi.fn()}
      />
    );

    expect(screen.getByText("Theo 5 khu vực địa lý")).toBeInTheDocument();
    expect(
      screen.getByText("Theo từng năm (1992 - 1998)")
    ).toBeInTheDocument();
    expect(screen.getByText("Theo phân khúc khách hàng")).toBeInTheDocument();

    // Kiểm tra có tiền tố ký tự nhận diện A, B, C
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
  });

  it("3. Click vào một chip tùy chọn sẽ kích hoạt onSelectOption với đúng chuỗi", () => {
    const handleSelect = vi.fn();
    const mockOptions = ["Theo 5 khu vực địa lý", "Theo từng năm"];

    render(
      <ClarificationCard
        question="Lựa chọn phương án:"
        options={mockOptions}
        onSelectOption={handleSelect}
      />
    );

    const firstOptionBtn = screen.getByRole("button", {
      name: /Theo 5 khu vực địa lý/i,
    });
    fireEvent.click(firstOptionBtn);

    expect(handleSelect).toHaveBeenCalledTimes(1);
    expect(handleSelect).toHaveBeenCalledWith("Theo 5 khu vực địa lý");
  });

  it("4. Hỗ trợ phím Enter và Space để kích hoạt lựa chọn (Accessibility)", () => {
    const handleSelect = vi.fn();
    const mockOptions = ["Phương án 1", "Phương án 2"];

    render(
      <ClarificationCard
        question="Lựa chọn:"
        options={mockOptions}
        onSelectOption={handleSelect}
      />
    );

    const secondOptionBtn = screen.getByRole("button", {
      name: /Phương án 2/i,
    });

    fireEvent.keyDown(secondOptionBtn, { key: "Enter", code: "Enter" });
    expect(handleSelect).toHaveBeenCalledWith("Phương án 2");

    fireEvent.keyDown(secondOptionBtn, { key: " ", code: "Space" });
    expect(handleSelect).toHaveBeenCalledWith("Phương án 2");
  });

  it("5. Khi disabled = true, toàn bộ các chip bị vô hiệu hóa và click không kích hoạt callback", () => {
    const handleSelect = vi.fn();
    const mockOptions = ["Lựa chọn A", "Lựa chọn B"];

    render(
      <ClarificationCard
        question="Lựa chọn:"
        options={mockOptions}
        onSelectOption={handleSelect}
        disabled={true}
      />
    );

    const buttons = screen.getAllByRole("button");
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });

    fireEvent.click(buttons[0]);
    expect(handleSelect).not.toHaveBeenCalled();
  });

  it("6. Xử lý an toàn khi không có options hoặc options rỗng", () => {
    const { container } = render(
      <ClarificationCard
        question="Câu hỏi không có lựa chọn cụ thể"
        options={[]}
        onSelectOption={vi.fn()}
      />
    );

    expect(
      screen.getByText("Câu hỏi không có lựa chọn cụ thể")
    ).toBeInTheDocument();
    expect(container.querySelectorAll("button").length).toBe(0);
  });
});
