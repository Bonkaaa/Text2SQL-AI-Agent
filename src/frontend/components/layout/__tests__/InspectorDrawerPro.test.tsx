import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { InspectorDrawer } from "../InspectorDrawer";

describe("InspectorDrawer Pro (Data Lineage Fact/Dim, PII Masking Audit)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. should classify tables into Fact and Dimension categories in Data Lineage", () => {
    render(
      <InspectorDrawer
        isOpen={true}
        onClose={vi.fn()}
        tablesUsed={["store_sales", "date_dim", "item", "customer"]}
      />
    );

    // Fact table badge
    expect(screen.getByText("store_sales")).toBeInTheDocument();
    expect(screen.getByText(/Fact Tables|Bảng Sự kiện/i)).toBeInTheDocument();

    // Dimension table badges
    expect(screen.getByText("date_dim")).toBeInTheDocument();
    expect(screen.getByText("item")).toBeInTheDocument();
    expect(screen.getByText(/Dimension Tables|Bảng Danh mục/i)).toBeInTheDocument();
  });

  it("2. should render list of masked PII columns with security lock icons", () => {
    render(
      <InspectorDrawer
        isOpen={true}
        onClose={vi.fn()}
        maskedColumns={["c_email_address", "ca_street_name"]}
      />
    );

    expect(screen.getByText("c_email_address")).toBeInTheDocument();
    expect(screen.getByText("ca_street_name")).toBeInTheDocument();
    expect(screen.getAllByText(/Che giấu tự động/i)[0]).toBeInTheDocument();
  });

  it("3. should trigger copy SQL and show feedback when clicking copy button", async () => {
    // Mock clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });

    render(
      <InspectorDrawer
        isOpen={true}
        onClose={vi.fn()}
        sql="SELECT * FROM store_sales LIMIT 10;"
      />
    );

    const copyBtn = screen.getByTitle(/Sao chép SQL/i);
    expect(copyBtn).toBeInTheDocument();

    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "SELECT * FROM store_sales LIMIT 10;"
    );
  });
});
