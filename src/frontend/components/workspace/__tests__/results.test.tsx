import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AnswerView } from "../views/AnswerView";
import { DataTableView } from "../views/DataTableView";
import { SQLViewer } from "../views/SQLViewer";
import { TraceView } from "../views/TraceView";
import { ResultCanvas } from "../ResultCanvas";
import { QueryResponse } from "@/types/api";

const mockResponse: QueryResponse = {
  session_id: "sess_100",
  status: "COMPLETED",
  question: "Top 10 products revenue",
  final_answer: "Top 10 items analyzed. Item-102 generated highest revenue.",
  sql: "SELECT i_item_id, SUM(ss_net_paid) AS revenue FROM store_sales GROUP BY 1 LIMIT 10;",
  data: [
    { i_item_id: "Item-102", revenue: 98400 },
    { i_item_id: "Item-204", revenue: 84700 },
  ],
  columns: ["i_item_id", "revenue"],
  response_package: {
    session_id: "sess_100",
    direct_answer: "Top 10 items analyzed. Item-102 generated highest revenue.",
    detailed_insight: [
      "Item-102 leads sales by 16% over runner up.",
      "Apparel category dominates the top 5.",
    ],
    artifacts: [
      {
        type: "kpi",
        title: "Top Product Revenue",
        value: 98400,
        unit: "USD",
        delta: 12.8,
        delta_type: "increase",
      },
      {
        type: "chart",
        chart_type: "bar",
        title: "Revenue by product",
        x_key: "i_item_id",
        y_keys: ["revenue"],
        data: [
          { i_item_id: "Item-102", revenue: 98400 },
          { i_item_id: "Item-204", revenue: 84700 },
        ],
      },
      {
        type: "table",
        title: "Revenue Table",
        columns: ["i_item_id", "revenue"],
        rows: [
          { i_item_id: "Item-102", revenue: 98400 },
          { i_item_id: "Item-204", revenue: 84700 },
        ],
      },
    ],
  },
  tasks: [
    { task_id: "t1", description: "Retrieve schema for item and store sales", status: "COMPLETED" },
    { task_id: "t2", description: "Execute SQL and aggregate net paid", status: "COMPLETED" },
  ],
  artifacts: [
    {
      artifact_id: "a1",
      task_id: "t1",
      sql: "SELECT i_item_id, SUM(ss_net_paid) AS revenue FROM store_sales GROUP BY 1 LIMIT 10;",
      dialect: "duckdb",
      tables_used: ["store_sales", "item", "date_dim"],
      status: "SUCCESS",
      row_count: 2,
      execution_time_ms: 186,
    },
  ],
  execution_time_ms: 1470,
};

describe("Result Canvas & Views (TDD Suite 4)", () => {
  describe("AnswerView", () => {
    it("should render executive summary and KPI cards", () => {
      render(
        <AnswerView
          response={mockResponse}
          onJumpToTable={vi.fn()}
        />
      );

      expect(screen.getByText(/Item-102 generated highest revenue/i)).toBeInTheDocument();
      expect(screen.getByText("Top Product Revenue")).toBeInTheDocument();
      expect(screen.getByText("$98.4K")).toBeInTheDocument();
      expect(screen.getByText(/Item-102 leads sales by 16%/i)).toBeInTheDocument();
    });
  });

  describe("DataTableView", () => {
    it("should render table headers and rows and support CSV export", () => {
      render(
        <DataTableView
          data={mockResponse.data!}
          columns={mockResponse.columns!}
        />
      );

      expect(screen.getByText("i_item_id")).toBeInTheDocument();
      expect(screen.getByText("Item-102")).toBeInTheDocument();
      expect(screen.getByText("Item-204")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Export CSV/i })).toBeInTheDocument();
    });
  });

  describe("SQLViewer", () => {
    it("should render formatted SQL and AST verified badge", () => {
      render(<SQLViewer sql={mockResponse.sql!} />);
      expect(screen.getByText(/SELECT/)).toBeInTheDocument();
      expect(screen.getByText(/store_sales/)).toBeInTheDocument();
      expect(screen.getByText("AST Verified")).toBeInTheDocument();
    });
  });

  describe("TraceView", () => {
    it("should render execution steps with tables used and timing", () => {
      render(<TraceView response={mockResponse} />);
      expect(screen.getByText(/Retrieve schema for item and store sales/i)).toBeInTheDocument();
      expect(screen.getByText(/store_sales, item, date_dim/i)).toBeInTheDocument();
      expect(screen.getByText("186ms")).toBeInTheDocument();
    });
  });

  describe("ResultCanvas", () => {
    it("should switch between tabs when clicked", () => {
      const handleTabChange = vi.fn();
      render(
        <ResultCanvas
          response={mockResponse}
          activeTab="chart"
          onTabChange={handleTabChange}
        />
      );

      const tableTab = screen.getByRole("tab", { name: /Table/i });
      fireEvent.click(tableTab);
      expect(handleTabChange).toHaveBeenCalledWith("table");
    });
  });
});
