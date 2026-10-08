import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { KPIArtifactGrid } from "../KPIArtifactGrid";
import { ExecutiveSummaryCard } from "../ExecutiveSummaryCard";
import type { KpiArtifact } from "../../../types/artifacts";

describe("KPIArtifactGrid component", () => {
  const mockKpis: KpiArtifact[] = [
    {
      type: "kpi",
      title: "Net Paid Sales",
      value: 12500000,
      unit: "USD",
      delta: 14.2,
      delta_type: "increase",
    },
    {
      type: "kpi",
      title: "Return Rate",
      value: "4.8%",
      delta: -1.5,
      delta_type: "decrease",
    },
    {
      type: "kpi",
      title: "Total Transactions",
      value: 84320,
    },
  ];

  it("should render all KPI cards with titles and formatted values", () => {
    render(<KPIArtifactGrid kpis={mockKpis} />);

    expect(screen.getByText("Net Paid Sales")).toBeInTheDocument();
    expect(screen.getByText("Return Rate")).toBeInTheDocument();
    expect(screen.getByText("Total Transactions")).toBeInTheDocument();

    // Check unit
    expect(screen.getByText("USD")).toBeInTheDocument();
    // Check formatted number for 84320 -> 84,320
    expect(screen.getByText(/84,320|84.320/)).toBeInTheDocument();
  });

  it("should display delta badges with correct styles for increase and decrease", () => {
    render(<KPIArtifactGrid kpis={mockKpis} />);

    const increaseBadge = screen.getByText("+14.2%");
    expect(increaseBadge).toBeInTheDocument();
    expect(increaseBadge.className).toContain("text-emerald-400");

    const decreaseBadge = screen.getByText("-1.5%");
    expect(decreaseBadge).toBeInTheDocument();
    expect(decreaseBadge.className).toContain("text-rose-400");
  });

  it("should return null if kpis array is empty", () => {
    const { container } = render(<KPIArtifactGrid kpis={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("ExecutiveSummaryCard component", () => {
  it("should render direct answer and key insights list", () => {
    render(
      <ExecutiveSummaryCard
        directAnswer="Doanh thu tăng trưởng mạnh mẽ trong Q4/2002."
        detailedInsight={[
          "Kênh Store Sales đóng góp 62% tổng doanh thu.",
          "Mặt hàng Electronics có biên lợi nhuận cao nhất.",
        ]}
      />
    );

    expect(
      screen.getByText("Doanh thu tăng trưởng mạnh mẽ trong Q4/2002.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Kênh Store Sales đóng góp 62% tổng doanh thu.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Mặt hàng Electronics có biên lợi nhuận cao nhất.")
    ).toBeInTheDocument();
  });

  it("should return null if neither directAnswer nor detailedInsight is provided", () => {
    const { container } = render(<ExecutiveSummaryCard />);
    expect(container.firstChild).toBeNull();
  });
});
