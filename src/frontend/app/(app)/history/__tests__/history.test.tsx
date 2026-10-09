import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import HistoryPage from "../page";
import { AuthProvider } from "@/context/AuthContext";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("Query History & Audit Page (TDD Suite 4)", () => {
  beforeEach(() => {
    mockPush.mockClear();
    localStorage.clear();
  });

  it("should render history table with questions, status badges, and latencies", () => {
    render(
      <AuthProvider>
        <HistoryPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Query history/i)).toBeInTheDocument();
    expect(screen.getByText(/Which 10 products generated the most revenue in 2003?/i)).toBeInTheDocument();
    expect(screen.getAllByText("SUCCESS").length).toBeGreaterThan(0);
    expect(screen.getByText("186ms")).toBeInTheDocument();
  });

  it("should filter history by status tabs", () => {
    render(
      <AuthProvider>
        <HistoryPage />
      </AuthProvider>
    );

    const blockedTab = screen.getByRole("tab", { name: /Blocked/i });
    fireEvent.click(blockedTab);

    expect(screen.getAllByText(/DROP TABLE customer;/i).length).toBeGreaterThan(0);
    expect(
      screen.queryByText(/Which 10 products generated the most revenue in 2003?/i)
    ).not.toBeInTheDocument();
  });

  it("should navigate to workspace with question when Rerun is clicked", () => {
    render(
      <AuthProvider>
        <HistoryPage />
      </AuthProvider>
    );

    const rerunBtns = screen.getAllByRole("button", { name: /Rerun/i });
    fireEvent.click(rerunBtns[0]);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/workspace?q=")
    );
  });
});
