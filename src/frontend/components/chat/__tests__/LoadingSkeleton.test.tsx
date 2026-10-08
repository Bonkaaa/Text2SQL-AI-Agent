import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingSkeleton } from "../LoadingSkeleton";

describe("Executive Loading Skeleton (Task 2.3)", () => {
  it("1. Render cấu trúc skeleton đa tầng gồm KPI cards, Chart area và Table rows", () => {
    render(<LoadingSkeleton />);

    // Phải có container có role status
    const statusContainer = screen.getByRole("status");
    expect(statusContainer).toBeInTheDocument();

    // Kiểm tra 3 thẻ KPI skeleton
    const kpiSkeletons = screen.getAllByTestId("kpi-skeleton-card");
    expect(kpiSkeletons.length).toBe(3);

    // Kiểm tra Chart skeleton area
    expect(screen.getByTestId("chart-skeleton-area")).toBeInTheDocument();

    // Kiểm tra Table rows skeleton
    const tableRowSkeletons = screen.getAllByTestId("table-row-skeleton");
    expect(tableRowSkeletons.length).toBeGreaterThanOrEqual(3);
  });

  it("2. Đảm bảo thuộc tính trợ năng aria-busy và aria-label", () => {
    render(<LoadingSkeleton />);

    const container = screen.getByRole("status");
    expect(container).toHaveAttribute("aria-busy", "true");
    expect(container).toHaveAttribute("aria-label", "Đang phân tích số liệu...");
  });
});
