import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DashboardPage from "../page";
import { AuthProvider } from "@/context/AuthContext";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("Dashboard Activity Chart & Popular Queries (TDD Suite 3)", () => {
  beforeEach(() => {
    mockPush.mockClear();
    localStorage.clear();
  });

  it("should render 7-Day Query Activity Volume section", () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    expect(screen.getByText(/7-Day Query Activity Volume/i)).toBeInTheDocument();
    expect(screen.getByText(/Daily executed analytical requests/i)).toBeInTheDocument();
    expect(screen.getByTestId("activity-chart-container")).toBeInTheDocument();
  });

  it("should render Recommended / Popular Queries list with 1-click execution", () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Popular Queries/i)).toBeInTheDocument();
    expect(
      screen.getByText("Top 10 Sản Phẩm Doanh Thu Cao Nhất 2003")
    ).toBeInTheDocument();

    const runButtons = screen.getAllByRole("button", { name: /Run in Workspace|Run/i });
    expect(runButtons.length).toBeGreaterThan(0);
  });

  it("should navigate to workspace with question query parameter when clicking Run in Workspace", () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    const runButtons = screen.getAllByRole("button", { name: /Run in Workspace|Run/i });
    fireEvent.click(runButtons[0]);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/workspace?q=")
    );
  });
});
