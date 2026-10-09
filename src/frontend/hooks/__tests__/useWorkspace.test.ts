import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useWorkspace } from "../useWorkspace";
import * as apiClient from "@/lib/api-client";
import { QueryResponse } from "@/types/api";

describe("useWorkspace Hook (TDD Suite 2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should initialize with default states and empty messages", () => {
    const { result } = renderHook(() => useWorkspace());

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.currentResponse).toBeNull();
    expect(result.current.activeTab).toBe("chart");
    expect(result.current.sessionId).toBeDefined();
  });

  it("should successfully handle a completed query response and select chart tab if chart exists", async () => {
    const mockCompleted: QueryResponse = {
      session_id: "sess_test",
      status: "COMPLETED",
      question: "Top 10 products revenue",
      final_answer: "Top 10 items analyzed.",
      sql: "SELECT i_item_id, SUM(ss_net_paid) FROM store_sales GROUP BY 1 LIMIT 10;",
      data: [{ i_item_id: "Item-1", total: 50000 }],
      columns: ["i_item_id", "total"],
      response_package: {
        session_id: "sess_test",
        direct_answer: "Top 10 items analyzed.",
        artifacts: [
          {
            type: "chart",
            chart_type: "bar",
            title: "Top 10 items",
            x_key: "i_item_id",
            y_keys: ["total"],
            data: [{ i_item_id: "Item-1", total: 50000 }],
          },
        ],
      },
      execution_time_ms: 1200,
    };

    vi.spyOn(apiClient, "askQuery").mockResolvedValueOnce(mockCompleted);

    const { result } = renderHook(() => useWorkspace());

    await act(async () => {
      await result.current.submitQuery("Top 10 products revenue");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("Top 10 products revenue");

    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].content).toBe("Top 10 items analyzed.");
    expect(result.current.messages[1].status).toBe("COMPLETED");

    expect(result.current.currentResponse).toEqual(mockCompleted);
    expect(result.current.activeTab).toBe("chart");
    expect(result.current.isLoading).toBe(false);
  });

  it("should handle CLARIFICATION_REQUIRED status and allow selecting options", async () => {
    const mockClarify: QueryResponse = {
      session_id: "sess_clarify",
      status: "CLARIFICATION_REQUIRED",
      question: "Doanh thu",
      is_ambiguous: true,
      clarification_question: "Chon kenh ban hang ban muon phan tich?",
      suggested_options: ["Store sales 2003", "Web sales 2003"],
      execution_time_ms: 300,
    };

    const mockFollowUp: QueryResponse = {
      session_id: "sess_clarify",
      status: "COMPLETED",
      question: "Store sales 2003",
      final_answer: "Store sales 2003 completed.",
      execution_time_ms: 800,
    };

    vi.spyOn(apiClient, "askQuery")
      .mockResolvedValueOnce(mockClarify)
      .mockResolvedValueOnce(mockFollowUp);

    const { result } = renderHook(() => useWorkspace());

    await act(async () => {
      await result.current.submitQuery("Doanh thu");
    });

    expect(result.current.messages[1].status).toBe("CLARIFICATION_REQUIRED");
    expect(result.current.messages[1].queryResponse?.suggested_options).toHaveLength(2);

    // Click option
    await act(async () => {
      await result.current.selectClarificationOption("Store sales 2003");
    });

    expect(result.current.messages).toHaveLength(4);
    expect(result.current.messages[2].content).toBe("Store sales 2003");
    expect(result.current.messages[3].content).toBe("Store sales 2003 completed.");
  });

  it("should handle HITL approval workflow", async () => {
    const mockHitlPending: QueryResponse = {
      session_id: "sess_hitl",
      status: "PENDING_APPROVAL",
      question: "Full scan scan large table",
      requires_hitl: true,
      estimated_cost_bytes: 52428800,
      sql: "SELECT * FROM store_sales;",
      execution_time_ms: 400,
    };

    const mockApproveRes = {
      session_id: "sess_hitl",
      approved: true,
      status: "SUCCESS",
      message: "Query approved and executed.",
      data: [{ id: 1, val: 100 }],
      columns: ["id", "val"],
    };

    vi.spyOn(apiClient, "askQuery").mockResolvedValueOnce(mockHitlPending);
    vi.spyOn(apiClient, "approveQuery").mockResolvedValueOnce(mockApproveRes);

    const { result } = renderHook(() => useWorkspace());

    await act(async () => {
      await result.current.submitQuery("Full scan scan large table");
    });

    expect(result.current.messages[1].status).toBe("PENDING_APPROVAL");

    await act(async () => {
      await result.current.approveHitl(true);
    });

    expect(result.current.messages[1].status).toBe("COMPLETED");
    expect(result.current.messages[1].content).toBe("Query approved and executed.");
    expect(result.current.currentResponse?.data).toEqual([{ id: 1, val: 100 }]);
  });
});
