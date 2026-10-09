import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WorkspacePage from "../page";
import * as apiClient from "@/lib/api-client";
import { getSavedQueries } from "@/lib/storage";
import { QueryResponse } from "@/types/api";

vi.mock("@/lib/api-client");

const mockResponse: QueryResponse = {
  session_id: "sess_save_test",
  status: "COMPLETED",
  question: "How many items were returned in store channel 2003?",
  final_answer: "There were 18,450 store returns recorded in 2003.",
  sql: "SELECT COUNT(*) FROM store_returns JOIN date_dim ON sr_returned_date_sk = d_date_sk WHERE d_year = 2003;",
  data: [{ return_count: 18450 }],
  columns: ["return_count"],
};

describe("Save Query Flow from Workspace (TDD Suite 5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("should allow user to save a query from ResultCanvas toolbar and verify it in storage", async () => {
    vi.mocked(apiClient.askQuery).mockResolvedValueOnce(mockResponse);

    render(<WorkspacePage />);

    // 1. Submit query
    const input = screen.getByPlaceholderText(/Ask a question about your data/i);
    fireEvent.change(input, {
      target: { value: "How many items were returned in store channel 2003?" },
    });

    const submitBtn = screen.getByRole("button", { name: /Send query/i });
    fireEvent.click(submitBtn);

    // 2. Wait for response
    await waitFor(() => {
      expect(
        screen.getByText(/There were 18,450 store returns recorded/i)
      ).toBeInTheDocument();
    });

    // 3. Find and click "Save query" button in ResultCanvas
    const saveBtn = screen.getByRole("button", { name: /Save query/i });
    fireEvent.click(saveBtn);

    // 4. Verify button toggles to Saved
    expect(screen.getByText(/Saved/i)).toBeInTheDocument();

    // 5. Verify item exists in storage
    const all = getSavedQueries();
    expect(
      all.some((q) => q.question === "How many items were returned in store channel 2003?")
    ).toBe(true);
  });
});
