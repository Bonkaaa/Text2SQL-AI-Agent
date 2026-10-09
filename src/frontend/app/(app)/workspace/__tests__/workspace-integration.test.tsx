import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WorkspacePage from "../page";
import * as apiClient from "@/lib/api-client";
import { QueryResponse } from "@/types/api";

vi.mock("@/lib/api-client");

const mockResponse: QueryResponse = {
  session_id: "sess_integration_1",
  status: "COMPLETED",
  question: "Top 10 products revenue",
  final_answer: "Top 10 products analyzed successfully. Item-102 leads sales.",
  sql: "SELECT i_item_id, SUM(ss_net_paid) AS revenue FROM store_sales GROUP BY 1 LIMIT 10;",
  data: [
    { i_item_id: "Item-102", revenue: 98400 },
    { i_item_id: "Item-204", revenue: 84700 },
  ],
  columns: ["i_item_id", "revenue"],
  response_package: {
    session_id: "sess_integration_1",
    direct_answer: "Top 10 products analyzed successfully. Item-102 leads sales.",
    detailed_insight: ["Item-102 leads sales by 16%."],
    artifacts: [
      {
        type: "kpi",
        title: "Top Product Revenue",
        value: 98400,
        unit: "USD",
      },
      {
        type: "chart",
        chart_type: "bar",
        title: "Revenue by Product",
        x_key: "i_item_id",
        y_keys: ["revenue"],
        data: [
          { i_item_id: "Item-102", revenue: 98400 },
          { i_item_id: "Item-204", revenue: 84700 },
        ],
      },
    ],
  },
  tasks: [
    {
      task_id: "t1",
      description: "Retrieve schema for item and store sales",
      status: "COMPLETED",
    },
  ],
  artifacts: [
    {
      artifact_id: "a1",
      task_id: "t1",
      sql: "SELECT i_item_id, SUM(ss_net_paid) AS revenue FROM store_sales GROUP BY 1 LIMIT 10;",
      dialect: "duckdb",
      tables_used: ["store_sales", "item"],
      status: "SUCCESS",
      execution_time_ms: 150,
      row_count: 2,
    },
  ],
  execution_time_ms: 850,
};

describe("Workspace Full Integration Flow (TDD Suite 5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should execute full query lifecycle, update messages, and render result tabs", async () => {
    vi.mocked(apiClient.askQuery).mockResolvedValueOnce(mockResponse);

    render(<WorkspacePage />);

    // 1. Initial State Checks
    expect(screen.getByText(/Ask your data/i)).toBeInTheDocument();
    expect(screen.getByText(/Ready for Analytics Exploration/i)).toBeInTheDocument();

    // 2. Submit a natural language question
    const input = screen.getByPlaceholderText(/Ask a question about your data/i);
    fireEvent.change(input, { target: { value: "Top 10 products revenue" } });

    const submitBtn = screen.getByRole("button", { name: /Send query/i });
    fireEvent.click(submitBtn);

    // 3. Verify user query and assistant response appear in conversation panel
    await waitFor(() => {
      expect(screen.getByText(/Item-102 leads sales/i)).toBeInTheDocument();
    });

    expect(apiClient.askQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        question: "Top 10 products revenue",
      }),
      undefined
    );

    // 4. Verify ResultCanvas automatically opened and shows result
    // Test switching to Table view
    const tableTab = screen.getByRole("tab", { name: /Table/i });
    fireEvent.click(tableTab);

    expect(screen.getByText("i_item_id")).toBeInTheDocument();
    expect(screen.getByText("Item-102")).toBeInTheDocument();
    expect(screen.getByText("Item-204")).toBeInTheDocument();

    // 5. Test switching to SQL view
    const sqlTab = screen.getByRole("tab", { name: /SQL/i });
    fireEvent.click(sqlTab);

    expect(screen.getByText(/store_sales/i)).toBeInTheDocument();
    expect(screen.getByText("AST Verified")).toBeInTheDocument();

    // 6. Test switching to Trace view
    const traceTab = screen.getByRole("tab", { name: /Trace/i });
    fireEvent.click(traceTab);

    expect(screen.getByText(/Retrieve schema for item and store sales/i)).toBeInTheDocument();
    expect(screen.getByText("150ms")).toBeInTheDocument();
  });
});
