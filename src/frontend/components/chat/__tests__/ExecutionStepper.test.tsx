import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ExecutionStepper } from "../ExecutionStepper";

describe("Authentic Live Execution Stepper (Task 2.2)", () => {
  it("1. Khi isLoading = true, hiển thị Live Activity Indicator và không render checkbox giả", () => {
    render(<ExecutionStepper isLoading={true} />);

    // Phải có thông điệp tiến trình động
    expect(
      screen.getByText(/Đang phân tích câu hỏi & đối soát dữ liệu TPC-DS/i)
    ).toBeInTheDocument();

    // Không render danh sách 4 bước giả định cũ
    expect(screen.queryByText(/1\. Làm rõ ý định:/i)).toBeNull();
    expect(screen.queryByText(/2\. Schema & Categorical Retriever:/i)).toBeNull();
  });

  it("2. Khi hoàn tất, hiển thị thời gian thực thi trung thực và trạng thái an toàn", () => {
    render(
      <ExecutionStepper
        isLoading={false}
        executionTimeMs={185}
        totalRows={42}
      />
    );

    // Hiển thị thời gian ms thực tế
    expect(screen.getByText(/185ms/i)).toBeInTheDocument();
    // Hiển thị số lượng bản ghi
    expect(screen.getByText(/42 bản ghi/i)).toBeInTheDocument();
    // Hiển thị trạng thái an toàn AST
    expect(screen.getByText(/SELECT-only/i)).toBeInTheDocument();
  });

  it("3. Bấm vào status pill cho phép toggle mở rộng xem chi tiết telemetry", () => {
    render(
      <ExecutionStepper
        isLoading={false}
        executionTimeMs={210}
        totalRows={10}
        tablesUsed={["store_sales", "date_dim"]}
      />
    );

    // Ban đầu chi tiết bảng chưa mở rộng
    expect(screen.queryByText("store_sales, date_dim")).toBeNull();

    // Bấm vào nút toggle telemetry
    const toggleBtn = screen.getByRole("button", { name: /chi tiết thực thi/i });
    fireEvent.click(toggleBtn);

    // Mở rộng chi tiết telemetry
    expect(screen.getByText(/Bảng tham chiếu:/i)).toBeInTheDocument();
    expect(screen.getByText(/store_sales/i)).toBeInTheDocument();
  });
});
