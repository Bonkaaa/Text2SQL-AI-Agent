import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { DynamicChart, ACCESSIBLE_PALETTE } from "../DynamicChart";
import type { ChartArtifact } from "../../../types/artifacts";

describe("DynamicChart Pro (6-Series & Multi-Artifact integration)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const sampleArtifact: ChartArtifact = {
    type: "chart",
    chart_type: "bar",
    title: "Doanh thu đa kênh TPC-DS (2002)",
    x_key: "channel",
    y_keys: ["net_paid", "net_profit"],
    series_labels: {
      net_paid: "Doanh thu thuần",
      net_profit: "Lợi nhuận gộp",
    },
    data: [
      { channel: "Store", net_paid: 5400000, net_profit: 1200000 },
      { channel: "Web", net_paid: 3200000, net_profit: 850000 },
      { channel: "Catalog", net_paid: 1800000, net_profit: 410000 },
    ],
  };

  it("1. should render directly from a ChartArtifact object", () => {
    render(<DynamicChart artifact={sampleArtifact} />);

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(
      screen.getByText("Doanh thu đa kênh TPC-DS (2002)")
    ).toBeInTheDocument();
  });

  it("2. should use Accessible 6-Series Palette (#3B82F6, #10B981, ...)", () => {
    expect(ACCESSIBLE_PALETTE).toBeDefined();
    expect(ACCESSIBLE_PALETTE[0]).toBe("#3B82F6"); // Blue
    expect(ACCESSIBLE_PALETTE[1]).toBe("#10B981"); // Emerald
    expect(ACCESSIBLE_PALETTE[2]).toBe("#F59E0B"); // Amber
    expect(ACCESSIBLE_PALETTE[3]).toBe("#8B5CF6"); // Violet
    expect(ACCESSIBLE_PALETTE[4]).toBe("#06B6D4"); // Cyan
    expect(ACCESSIBLE_PALETTE[5]).toBe("#EC4899"); // Rose
  });

  it("3. should switch chart types between Bar, Line, Area smoothly", () => {
    render(<DynamicChart artifact={sampleArtifact} />);

    const lineBtn = screen.getByRole("button", { name: /Đường/i });
    fireEvent.click(lineBtn);
    expect(lineBtn).toHaveAttribute("aria-pressed", "true");

    const areaBtn = screen.getByRole("button", { name: /Miền/i });
    fireEvent.click(areaBtn);
    expect(areaBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("4. should maintain backward compatibility with legacy config & data props", () => {
    render(
      <DynamicChart
        config={{
          chart_type: "bar",
          title: "Legacy Chart",
          x_key: "item",
          y_keys: ["val"],
        }}
        data={[{ item: "A", val: 10 }]}
      />
    );

    expect(screen.getByText("Legacy Chart")).toBeInTheDocument();
  });
});
