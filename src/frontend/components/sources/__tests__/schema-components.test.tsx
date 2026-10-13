import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DataSourceCard } from "../DataSourceCard";
import { TableDetailView } from "../TableDetailView";
import { SchemaExplorer } from "../SchemaExplorer";
import { TPCH_TABLES, getTableByName } from "@/data/tpchCatalog";

describe("Schema Explorer Components (TDD Suite 3)", () => {
  describe("DataSourceCard", () => {
    it("should render DuckDB connection status, table count, and dialect", () => {
      render(<DataSourceCard tableCount={8} />);
      expect(screen.getByText(/DuckDB TPC-H/i)).toBeInTheDocument();
      expect(screen.getByText(/Connected/i)).toBeInTheDocument();
      expect(screen.getByText("8")).toBeInTheDocument();
    });
  });

  describe("TableDetailView", () => {
    it("should display table details, columns with PK/FK, and trigger question click", () => {
      const lineitem = getTableByName("lineitem")!;
      const handleAsk = vi.fn();

      render(
        <TableDetailView
          table={lineitem}
          onAskQuestion={handleAsk}
        />
      );

      expect(screen.getByText("lineitem")).toBeInTheDocument();
      expect(screen.getByText(/l_extendedprice/i)).toBeInTheDocument();
      expect(screen.getAllByText(/PK/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/FK/i).length).toBeGreaterThan(0);

      const askBtn = screen.getByRole("button", { name: /Hỏi về bảng này/i });
      fireEvent.click(askBtn);
      expect(handleAsk).toHaveBeenCalled();
    });
  });

  describe("SchemaExplorer", () => {
    it("should search and filter tables by category tabs", () => {
      const handleSelect = vi.fn();
      const handleAsk = vi.fn();

      render(
        <SchemaExplorer
          tables={TPCH_TABLES}
          selectedTable={TPCH_TABLES[0]}
          onSelectTable={handleSelect}
          onAskQuestion={handleAsk}
        />
      );

      // Verify category tabs exist
      expect(screen.getByRole("tab", { name: /All/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Transactions/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Products & Inventory/i })).toBeInTheDocument();

      // Click Transactions tab
      fireEvent.click(screen.getByRole("tab", { name: /Transactions/i }));
      expect(screen.getAllByText("orders").length).toBeGreaterThan(0);
      expect(screen.getByText("lineitem")).toBeInTheDocument();

      // Switch back to All tab for global search
      fireEvent.click(screen.getByRole("tab", { name: /All/i }));
      const searchInput = screen.getByPlaceholderText(/Search tables/i);
      fireEvent.change(searchInput, { target: { value: "customer" } });
      expect(screen.getAllByText("customer").length).toBeGreaterThan(0);
    });
  });
});
