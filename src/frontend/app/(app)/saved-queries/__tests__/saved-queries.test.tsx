import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SavedQueriesPage from "../page";
import { AuthProvider } from "@/context/AuthContext";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("Saved Queries Page (TDD Suite 3)", () => {
  beforeEach(() => {
    mockPush.mockClear();
    localStorage.clear();
  });

  it("should render preset saved queries and header", () => {
    render(
      <AuthProvider>
        <SavedQueriesPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Saved queries/i)).toBeInTheDocument();
    expect(screen.getByText(/Top 10 Khách Hàng Chi Tiêu Cao Nhất Năm 1995/i)).toBeInTheDocument();
  });

  it("should open query in workspace when Open is clicked", () => {
    render(
      <AuthProvider>
        <SavedQueriesPage />
      </AuthProvider>
    );

    const openBtns = screen.getAllByRole("button", { name: /Open/i });
    fireEvent.click(openBtns[0]);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/workspace?q=")
    );
  });

  it("should search and filter saved queries", () => {
    render(
      <AuthProvider>
        <SavedQueriesPage />
      </AuthProvider>
    );

    const searchInput = screen.getByPlaceholderText(/Search saved queries/i);
    fireEvent.change(searchInput, { target: { value: "Đổi Trả" } });

    expect(screen.getByText(/Phân Tích Tỷ Lệ Đổi Trả/i)).toBeInTheDocument();
    expect(screen.queryByText(/Doanh Thu Theo Từng Phân Khúc/i)).not.toBeInTheDocument();
  });

  it("should delete a saved query when delete is confirmed", () => {
    render(
      <AuthProvider>
        <SavedQueriesPage />
      </AuthProvider>
    );

    const deleteBtns = screen.getAllByTitle(/Delete saved query/i);
    const initialCount = deleteBtns.length;

    fireEvent.click(deleteBtns[0]);

    // Check count decreased
    const remaining = screen.queryAllByTitle(/Delete saved query/i);
    expect(remaining.length).toBe(initialCount - 1);
  });
});
