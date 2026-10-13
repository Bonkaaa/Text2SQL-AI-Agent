import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DataSourcesPage from "../page";
import { AuthProvider } from "@/context/AuthContext";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("Data Sources Full Integration Flow (TDD Suite 5)", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("should render full 8-table TPC-H explorer, inspect columns, and trigger question navigation", () => {
    render(
      <AuthProvider>
        <DataSourcesPage />
      </AuthProvider>
    );

    // 1. Verify Page Heading & DuckDB Connection Card
    expect(screen.getByText(/Data sources & Schema/i)).toBeInTheDocument();
    expect(screen.getByText(/DuckDB TPC-H Benchmark/i)).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();

    // 2. Verify Table Catalog in Explorer
    expect(screen.getAllByText("orders").length).toBeGreaterThan(0);
    expect(screen.getByText("lineitem")).toBeInTheDocument();

    // 3. Inspect columns
    expect(screen.getByText(/o_totalprice/i)).toBeInTheDocument();
    expect(screen.getAllByText(/PK/i).length).toBeGreaterThan(0);

    // 4. Click Ask about table
    const askBtn = screen.getByRole("button", { name: /Hỏi về bảng này/i });
    fireEvent.click(askBtn);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/workspace?q=")
    );
  });
});
