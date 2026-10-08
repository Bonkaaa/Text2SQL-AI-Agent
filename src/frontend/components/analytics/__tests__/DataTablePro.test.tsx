import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { DataTable } from "../DataTable";
import type { TableArtifact } from "../../../types/artifacts";

describe("DataTable Pro (Artifact contract, Sticky Header, Markdown Copy & Density)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });
  });

  const sampleArtifact: TableArtifact = {
    type: "table",
    title: "Doanh thu chi tiết theo kênh và năm",
    columns: ["channel", "year", "net_paid", "item_count"],
    column_formats: {
      net_paid: "currency",
      item_count: "integer",
    },
    rows: [
      { channel: "Store", year: 2002, net_paid: 12500000, item_count: 45000 },
      { channel: "Web", year: 2002, net_paid: 4800000, item_count: 18200 },
      { channel: "Catalog", year: 2002, net_paid: 2100000, item_count: 8500 },
    ],
    total_row_count: 3,
  };

  it("1. should render directly from a TableArtifact object", () => {
    render(<DataTable artifact={sampleArtifact} />);

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(screen.getByText("channel")).toBeInTheDocument();
    expect(screen.getByText("net_paid")).toBeInTheDocument();
    expect(screen.getByText("Store")).toBeInTheDocument();
  });

  it("2. should align numeric columns to the right with font-mono-data tabular-nums", () => {
    render(<DataTable artifact={sampleArtifact} />);

    const netPaidCells = screen.getAllByText(/12,500,000|12.500.000/);
    expect(netPaidCells.length).toBeGreaterThan(0);
    const cell = netPaidCells[0].closest("td");
    expect(cell?.className).toContain("text-right");
    expect(cell?.className).toContain("font-mono-data");
  });

  it("3. should copy markdown table to clipboard when Copy button is clicked", async () => {
    render(<DataTable artifact={sampleArtifact} enableCopyMarkdown={true} />);

    const copyBtn = screen.getByRole("button", { name: /Sao chép Markdown|Copy Markdown/i });
    expect(copyBtn).toBeInTheDocument();

    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);
      const copiedText = (navigator.clipboard.writeText as any).mock.calls[0][0];
      expect(copiedText).toContain("| channel | year | net_paid | item_count |");
      expect(copiedText).toContain("| Store | 2002 |");
    });
  });

  it("4. should toggle density between Comfortable and Compact", () => {
    render(<DataTable artifact={sampleArtifact} />);

    const densityBtn = screen.getByRole("button", { name: /Mật độ|Compact|Comfortable/i });
    expect(densityBtn).toBeInTheDocument();

    fireEvent.click(densityBtn);
    // Sau khi click, kiểm tra xem bảng có đổi sang mật độ compact không
    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThan(1);
  });

  it("5. should have sticky header class on the table header", () => {
    render(<DataTable artifact={sampleArtifact} />);

    const thead = document.querySelector("thead");
    expect(thead?.className).toContain("sticky");
  });
});
