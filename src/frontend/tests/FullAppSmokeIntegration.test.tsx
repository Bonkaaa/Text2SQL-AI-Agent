import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthProvider } from "@/context/AuthContext";

// Import all 7 main pages
import LoginPage from "@/app/(auth)/login/page";
import WorkspacePage from "@/app/(app)/workspace/page";
import DashboardPage from "@/app/(app)/dashboard/page";
import DataSourcesPage from "@/app/(app)/data-sources/page";
import SavedQueriesPage from "@/app/(app)/saved-queries/page";
import HistoryPage from "@/app/(app)/history/page";
import SettingsPage from "@/app/(app)/settings/page";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/dashboard",
}));

describe("Full Application Smoke Integration (TDD Suite 5)", () => {
  beforeEach(() => {
    localStorage.clear();
    mockPush.mockClear();
  });

  it("1. should render Login page without errors", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Welcome to QueryPilot/i)).toBeInTheDocument();
    expect(screen.getByText(/1-Click Demo Persona/i)).toBeInTheDocument();
  });

  it("2. should render Workspace page without errors", () => {
    render(
      <AuthProvider>
        <WorkspacePage />
      </AuthProvider>
    );

    expect(screen.getByText(/Ask your data/i)).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Ask a question about your data/i)
    ).toBeInTheDocument();
  });

  it("3. should render Dashboard page without errors", () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Workspace Dashboard/i)).toBeInTheDocument();
    expect(screen.getByTestId("kpi-total-queries")).toBeInTheDocument();
    expect(screen.getByTestId("activity-chart-container")).toBeInTheDocument();
  });

  it("4. should render Data Sources (24 TPC-DS Tables) page without errors", () => {
    render(
      <AuthProvider>
        <DataSourcesPage />
      </AuthProvider>
    );

    expect(
      screen.getByRole("heading", { name: /Data sources & Schema/i })
    ).toBeInTheDocument();
    expect(screen.getAllByText(/store_sales/i).length).toBeGreaterThan(0);
  });

  it("5. should render Saved Queries library page without errors", () => {
    render(
      <AuthProvider>
        <SavedQueriesPage />
      </AuthProvider>
    );

    expect(screen.getByRole("heading", { name: /Saved queries/i })).toBeInTheDocument();
    expect(
      screen.getByText(/Top 10 Sản Phẩm Doanh Thu Cao Nhất 2003/i)
    ).toBeInTheDocument();
  });

  it("6. should render History & Audit Log page without errors", () => {
    render(
      <AuthProvider>
        <HistoryPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Query history/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Which 10 products generated the most revenue in 2003?/i)
    ).toBeInTheDocument();
  });

  it("7. should render Workspace Settings page without errors", () => {
    render(
      <AuthProvider>
        <SettingsPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Workspace Settings/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Analyst Profile/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: /Strict Read-Only SELECT Mode/i })
    ).toBeInTheDocument();
  });
});
