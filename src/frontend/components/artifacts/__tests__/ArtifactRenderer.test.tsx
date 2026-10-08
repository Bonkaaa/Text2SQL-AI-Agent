import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { ArtifactRenderer } from "../ArtifactRenderer";
import type { ArtifactItem } from "../../../types/artifacts";

describe("ArtifactRenderer component", () => {
  const mockArtifacts: ArtifactItem[] = [
    {
      type: "kpi",
      title: "Tổng doanh thu",
      value: 12500000,
      unit: "USD",
      delta: 14.2,
      delta_type: "increase",
    },
    {
      type: "kpi",
      title: "Tổng đơn hàng",
      value: 84320,
    },
    {
      type: "chart",
      chart_type: "bar",
      title: "Biểu đồ phân phối kênh",
      x_key: "channel",
      y_keys: ["val"],
      data: [{ channel: "Store", val: 100 }],
    },
    {
      type: "table",
      title: "Bảng chi tiết giao dịch",
      columns: ["id", "amount"],
      rows: [{ id: 1, amount: 50 }],
      total_row_count: 1,
    },
    {
      type: "evidence",
      task_id: "task_1",
      claim: "Kênh Store có tỷ suất lợi nhuận cao nhất",
      supporting_sql: "SELECT channel, profit FROM ...",
      sample_values: [{ channel: "Store", profit: 24.5 }],
    },
    {
      type: "callout",
      variant: "warning",
      message: "Cảnh báo: Dữ liệu chưa tính đến đơn hàng hoàn trả trong 7 ngày gần nhất.",
    },
    {
      type: "file",
      file_name: "sales_report_2002.csv",
      file_type: "csv",
      download_url: "https://example.com/download/sales.csv",
    },
  ];

  it("1. should render all distinct artifact types properly", () => {
    render(
      <ArtifactRenderer
        artifacts={mockArtifacts}
        directAnswer="Doanh thu tăng trưởng mạnh mẽ trong năm 2002."
        detailedInsight={["Đóng góp lớn nhất từ kênh Store."]}
      />
    );

    // Executive summary
    expect(screen.getByText("Doanh thu tăng trưởng mạnh mẽ trong năm 2002.")).toBeInTheDocument();
    expect(screen.getByText("Đóng góp lớn nhất từ kênh Store.")).toBeInTheDocument();

    // KPIs
    expect(screen.getByText("Tổng doanh thu")).toBeInTheDocument();
    expect(screen.getByText("Tổng đơn hàng")).toBeInTheDocument();

    // Chart
    expect(screen.getByText("Biểu đồ phân phối kênh")).toBeInTheDocument();

    // Table
    expect(screen.getByText("Bảng chi tiết giao dịch")).toBeInTheDocument();

    // Evidence
    expect(screen.getByText("Kênh Store có tỷ suất lợi nhuận cao nhất")).toBeInTheDocument();
    expect(screen.getByText("task_1")).toBeInTheDocument();

    // Callout
    expect(
      screen.getByText(/Cảnh báo: Dữ liệu chưa tính đến đơn hàng hoàn trả/i)
    ).toBeInTheDocument();

    // File
    expect(screen.getByText("sales_report_2002.csv")).toBeInTheDocument();
  });

  it("2. should apply dashboard_grid class when layout is dashboard_grid", () => {
    const { container } = render(
      <ArtifactRenderer
        artifacts={mockArtifacts.slice(2, 4)} // Chart and Table
        layout="dashboard_grid"
      />
    );

    const gridContainer = container.querySelector(".grid");
    expect(gridContainer).toBeInTheDocument();
  });

  it("3. should return null if artifacts and summary are empty", () => {
    const { container } = render(<ArtifactRenderer artifacts={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
