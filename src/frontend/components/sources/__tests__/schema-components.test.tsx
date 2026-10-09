import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DataSourceCard } from "../DataSourceCard";
import { TableDetailView } from "../TableDetailView";
import { SchemaExplorer } from "../SchemaExplorer";
import { TPCDS_TABLES, getTableByName } from "@/data/tpcdsCatalog";

describe("Schema Explorer Components (TDD Suite 3)", () => {
  describe("DataSourceCard", () => {
    it("should render DuckDB connection status, table count, and dialect", () => {
      render(<DataSourceCard tableCount={24} />);
      expect(screen.getByText(/DuckDB TPC-DS/i)).toBeInTheDocument();
      expect(screen.getByText(/Connected/i)).toBeInTheDocument();
      expect(screen.getByText("24")).toBeInTheDocument();
    });
  });

  describe("TableDetailView", () => {
    it("should display table details, columns with PK/FK, and trigger question click", () => {
      const storeSales = getTableByName("store_sales")!;
      const handleAsk = vi.fn();

      render(
        <TableDetailView
          table={storeSales}
          onAskQuestion={handleAsk}
        />
      );

      expect(screen.getByText("store_sales")).toBeInTheDocument();
      expect(screen.getByText(/ss_net_paid/i)).toBeInTheDocument();
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
          tables={TPCDS_TABLES}
          selectedTable={TPCDS_TABLES[0]}
          onSelectTable={handleSelect}
          onAskQuestion={handleAsk}
        />
      );

      // Verify category tabs exist
      expect(screen.getByRole("tab", { name: /All/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Sales/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Returns/i })).toBeInTheDocument();

      // Click Sales tab
      fireEvent.click(screen.getByRole("tab", { name: /Sales/i }));
      expect(screen.getAllByText("store_sales").length).toBeGreaterThan(0);
      expect(screen.getByText("web_sales")).toBeInTheDocument();

      // Switch back to All tab for global search
      fireEvent.click(screen.getByRole("tab", { name: /All/i }));
      const searchInput = screen.getByPlaceholderText(/Search tables/i);
      fireEvent.change(searchInput, { target: { value: "customer" } });
      expect(screen.getAllByText("customer").length).toBeGreaterThan(0);
    });
  });
});
