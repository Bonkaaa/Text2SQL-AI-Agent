import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import DashboardPage from "../page";
import { AuthProvider } from "@/context/AuthContext";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("Dashboard Dynamic KPIs (TDD Suite 2)", () => {
  beforeEach(() => {
    localStorage.clear();
    mockPush.mockClear();
  });

  it("should calculate and display default KPIs from history and saved queries", () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    // Default preset history has 4 items: 3 SUCCESS (186ms, 342ms, 154ms), 1 BLOCKED (12ms)
    // Avg latency of success: (186 + 342 + 154) / 3 = 227ms
    // Success rate: 3/4 = 75.0%
    const totalQueries = screen.getByTestId("kpi-total-queries");
    expect(totalQueries).toHaveTextContent("4");

    const successRate = screen.getByTestId("kpi-success-rate");
    expect(successRate).toHaveTextContent("75.0%");

    const avgLatency = screen.getByTestId("kpi-avg-latency");
    expect(avgLatency).toHaveTextContent("227ms");

    const savedCount = screen.getByTestId("kpi-saved-queries");
    expect(savedCount).toHaveTextContent(/3/);
  });

  it("should reflect updated counts when localStorage has custom items", () => {
    const customHistory = [
      {
        id: "c1",
        question: "Query 1",
        status: "SUCCESS",
        executionTimeMs: 100,
        timestamp: "2026-10-09 10:00",
      },
      {
        id: "c2",
        question: "Query 2",
        status: "SUCCESS",
        executionTimeMs: 200,
        timestamp: "2026-10-09 10:05",
      },
    ];

    const customSaved = [
      {
        id: "s1",
        title: "Saved 1",
        question: "Saved Q1",
        createdAt: "2026-10-09 10:00",
      },
    ];

    localStorage.setItem("querypilot_query_history", JSON.stringify(customHistory));
    localStorage.setItem("querypilot_saved_queries", JSON.stringify(customSaved));

    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    const totalQueries = screen.getByTestId("kpi-total-queries");
    expect(totalQueries).toHaveTextContent("2");

    const successRate = screen.getByTestId("kpi-success-rate");
    expect(successRate).toHaveTextContent("100.0%");

    const avgLatency = screen.getByTestId("kpi-avg-latency");
    expect(avgLatency).toHaveTextContent("150ms");

    const savedCount = screen.getByTestId("kpi-saved-queries");
    expect(savedCount).toHaveTextContent(/1/);
  });

  it("should handle empty history and saved queries without error", () => {
    localStorage.setItem("querypilot_query_history", JSON.stringify([]));
    localStorage.setItem("querypilot_saved_queries", JSON.stringify([]));

    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    expect(screen.getByTestId("kpi-total-queries")).toHaveTextContent("0");
    expect(screen.getByTestId("kpi-success-rate")).toHaveTextContent("0.0%");
    expect(screen.getByTestId("kpi-avg-latency")).toHaveTextContent("0ms");
    expect(screen.getByTestId("kpi-saved-queries")).toHaveTextContent(/0/);
  });
});
