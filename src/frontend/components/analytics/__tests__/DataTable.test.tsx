import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { DataTable } from "../DataTable";
import * as exportService from "@/services/exportCsv";

// Mock exportToCsv function
vi.mock("@/services/exportCsv", () => ({
  exportToCsv: vi.fn(),
}));

describe("Component 4.3: DataTable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const columns = ["r_name", "total_revenue", "order_count"];
  const sampleData = [
    { r_name: "ASIA", total_revenue: 250000, order_count: 120 },
    { r_name: "EUROPE", total_revenue: 190000, order_count: 95 },
    { r_name: "AMERICA", total_revenue: 210000, order_count: 110 },
    { r_name: "AFRICA", total_revenue: 120000, order_count: 60 },
    { r_name: "MIDDLE EAST", total_revenue: 150000, order_count: 80 },
    { r_name: "OCEANIA", total_revenue: 80000, order_count: 45 },
  ];

  it("1. Render tiêu đề các cột và dữ liệu dòng của trang đầu tiên", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData}
        initialPageSize={5}
      />
    );

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(screen.getByText("r_name")).toBeInTheDocument();
    expect(screen.getByText("total_revenue")).toBeInTheDocument();
    expect(screen.getByText("order_count")).toBeInTheDocument();

    // Dòng trang 1
    expect(screen.getByText("ASIA")).toBeInTheDocument();
    expect(screen.getByText("EUROPE")).toBeInTheDocument();
    // OCEANIA ở trang 2 nên không xuất hiện ở trang 1
    expect(screen.queryByText("OCEANIA")).not.toBeInTheDocument();
  });

  it("2. Sắp xếp cột khi click vào tiêu đề cột (Sort asc / desc)", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData}
        initialPageSize={10}
      />
    );

    const sortButton = screen.getByRole("button", {
      name: /Sắp xếp cột total_revenue/i,
    });
    expect(sortButton).toBeInTheDocument();

    // Click lần 1: Sắp xếp tăng dần (asc) -> Giá trị nhỏ nhất (80000 OCEANIA) lên đầu
    fireEvent.click(sortButton);
    const rowsAsc = screen.getAllByRole("row");
    expect(rowsAsc[1]).toHaveTextContent("OCEANIA");

    // Click lần 2: Sắp xếp giảm dần (desc) -> Giá trị lớn nhất (250000 ASIA) lên đầu
    fireEvent.click(sortButton);
    const rowsDesc = screen.getAllByRole("row");
    expect(rowsDesc[1]).toHaveTextContent("ASIA");
  });

  it("3. Lọc nhanh dữ liệu qua ô tìm kiếm (Search filter)", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData}
        initialPageSize={10}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Tìm kiếm trong bảng/i);
    expect(searchInput).toBeInTheDocument();

    // Nhập "EUROPE"
    fireEvent.change(searchInput, { target: { value: "EUROPE" } });

    expect(screen.getByText("EUROPE")).toBeInTheDocument();
    expect(screen.queryByText("ASIA")).not.toBeInTheDocument();
    expect(screen.queryByText("AMERICA")).not.toBeInTheDocument();
  });

  it("4. Phân trang điều hướng trang trước và trang sau", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData}
        initialPageSize={5}
      />
    );

    // Kiểm tra dòng thông tin phân trang: Hiển thị 1 - 5 của 6 dòng
    expect(screen.getByText(/Hiển thị 1 - 5 của 6 dòng/i)).toBeInTheDocument();

    const nextBtn = screen.getByRole("button", { name: /Trang sau/i });
    expect(nextBtn).toBeEnabled();

    // Click sang trang sau
    fireEvent.click(nextBtn);
    expect(screen.getByText(/Hiển thị 6 - 6 của 6 dòng/i)).toBeInTheDocument();
    expect(screen.getByText("OCEANIA")).toBeInTheDocument();
    expect(screen.queryByText("ASIA")).not.toBeInTheDocument();

    // Click quay lại trang trước
    const prevBtn = screen.getByRole("button", { name: /Trang trước/i });
    fireEvent.click(prevBtn);
    expect(screen.getByText("ASIA")).toBeInTheDocument();
  });

  it("5. Xuất file CSV khi bấm nút [Xuất CSV]", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData}
        tableName="tpch_revenue"
        enableExport={true}
      />
    );

    const exportBtn = screen.getByRole("button", { name: /Xuất CSV/i });
    expect(exportBtn).toBeInTheDocument();

    fireEvent.click(exportBtn);

    expect(exportService.exportToCsv).toHaveBeenCalledTimes(1);
    expect(exportService.exportToCsv).toHaveBeenCalledWith(
      expect.stringContaining("tpch_revenue"),
      columns,
      sampleData
    );
  });

  it("6. Hiển thị thông báo khi bộ lọc tìm kiếm không có kết quả", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData}
        initialPageSize={5}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Tìm kiếm trong bảng/i);
    fireEvent.change(searchInput, { target: { value: "NON_EXISTENT_VALUE" } });

    expect(
      screen.getByText(/Không tìm thấy dữ liệu phù hợp/i)
    ).toBeInTheDocument();
  });
});
