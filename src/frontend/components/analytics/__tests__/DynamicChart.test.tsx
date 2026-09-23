import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { DynamicChart } from "../DynamicChart";
import { RechartsConfig } from "@/types/api";

describe("Component 4.2: DynamicChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const sampleData = [
    { r_name: "ASIA", total_revenue: 250000000 },
    { r_name: "EUROPE", total_revenue: 190000000 },
    { r_name: "AMERICA", total_revenue: 210000000 },
    { r_name: "AFRICA", total_revenue: 120000000 },
    { r_name: "MIDDLE EAST", total_revenue: 150000000 },
  ];

  const barConfig: RechartsConfig = {
    chart_type: "bar",
    title: "Doanh thu thuần theo khu vực TPC-H",
    description: "So sánh doanh thu giữa 5 khu vực địa lý lớn",
    x_key: "r_name",
    y_keys: ["total_revenue"],
    series_labels: {
      total_revenue: "Tổng doanh thu",
    },
    legend: true,
  };

  it("1. Render tiêu đề, mô tả và vùng chứa biểu đồ cột (Bar Chart)", () => {
    render(<DynamicChart config={barConfig} data={sampleData} />);

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(
      screen.getByText("Doanh thu thuần theo khu vực TPC-H")
    ).toBeInTheDocument();
    expect(
      screen.getByText("So sánh doanh thu giữa 5 khu vực địa lý lớn")
    ).toBeInTheDocument();
  });

  it("2. Render biểu đồ đường (Line Chart) đúng cấu hình", () => {
    const lineConfig: RechartsConfig = {
      ...barConfig,
      chart_type: "line",
      title: "Biến động doanh thu theo thời gian",
    };

    render(<DynamicChart config={lineConfig} data={sampleData} />);
    expect(
      screen.getByText("Biến động doanh thu theo thời gian")
    ).toBeInTheDocument();
  });

  it("3. Render biểu đồ miền (Area Chart) đúng cấu hình", () => {
    const areaConfig: RechartsConfig = {
      ...barConfig,
      chart_type: "area",
      title: "Xu hướng tích lũy doanh số",
    };

    render(<DynamicChart config={areaConfig} data={sampleData} />);
    expect(
      screen.getByText("Xu hướng tích lũy doanh số")
    ).toBeInTheDocument();
  });

  it("4. Render biểu đồ tròn (Pie Chart) đúng cấu hình", () => {
    const pieConfig: RechartsConfig = {
      ...barConfig,
      chart_type: "pie",
      title: "Thị phần doanh thu theo khu vực",
    };

    render(<DynamicChart config={pieConfig} data={sampleData} />);
    expect(
      screen.getByText("Thị phần doanh thu theo khu vực")
    ).toBeInTheDocument();
  });

  it("5. Cho phép chuyển đổi linh hoạt loại biểu đồ qua thanh công cụ (Chart Type Switcher)", () => {
    render(<DynamicChart config={barConfig} data={sampleData} />);

    // Kiểm tra có các nút chuyển đổi: Cột, Đường, Miền, Tròn
    const lineButton = screen.getByRole("button", { name: /Đường/i });
    expect(lineButton).toBeInTheDocument();

    fireEvent.click(lineButton);
    // Nút Đường chuyển sang trạng thái active (được chọn)
    expect(lineButton).toHaveAttribute("aria-pressed", "true");
  });

  it("6. Hiển thị thông báo rỗng thân thiện (Empty State) khi dữ liệu rỗng", () => {
    render(<DynamicChart config={barConfig} data={[]} />);

    expect(
      screen.getByText(/Không có dữ liệu để vẽ biểu đồ/i)
    ).toBeInTheDocument();
  });
});
