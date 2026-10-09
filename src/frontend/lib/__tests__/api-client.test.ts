import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { askQuery, approveQuery } from "../api-client";
import { AskQueryRequest, ApprovalRequest, QueryResponse } from "@/types/api";

describe("API Client Module", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("should successfully send an askQuery request with default headers", async () => {
    const mockResponse: QueryResponse = {
      session_id: "sess_123",
      status: "COMPLETED",
      question: "Top 10 products",
      final_answer: "Item-102 generated the highest revenue.",
      sql: "SELECT * FROM store_sales LIMIT 10;",
      data: [{ item: "Item-102", revenue: 98400 }],
      columns: ["item", "revenue"],
      execution_time_ms: 1420,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const req: AskQueryRequest = {
      question: "Top 10 products",
      session_id: "sess_123",
      user_id: "analyst_alex",
      role: "Analyst",
    };

    const result = await askQuery(req);

    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [url, options] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/query/ask");
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(options.headers["X-User-Role"]).toBe("Analyst");
    expect(options.headers["X-User-Id"]).toBe("analyst_alex");
    expect(options.headers["X-Session-Id"]).toBe("sess_123");
  });

  it("should handle CLARIFICATION_REQUIRED response properly", async () => {
    const mockResponse: QueryResponse = {
      session_id: "sess_clarify",
      status: "CLARIFICATION_REQUIRED",
      question: "Doanh thu the nao",
      is_ambiguous: true,
      clarification_question: "Ban muon xem doanh thu theo nam hay theo kenh ban hang?",
      suggested_options: [
        "Doanh thu kenh Store nam 2003",
        "Doanh thu kenh Web nam 2003",
      ],
      execution_time_ms: 450,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await askQuery({ question: "Doanh thu the nao" });

    expect(result.status).toBe("CLARIFICATION_REQUIRED");
    expect(result.suggested_options).toHaveLength(2);
    expect(result.suggested_options?.[0]).toContain("Doanh thu kenh Store");
  });

  it("should throw a formatted error on HTTP 500 / network failure", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Database connection failed" }),
    });

    await expect(askQuery({ question: "Broken query" })).rejects.toThrow(
      "Database connection failed"
    );
  });

  it("should send approval request with Admin role and X-Admin-Token when approved", async () => {
    const mockApproveResponse = {
      session_id: "sess_hitl",
      approved: true,
      status: "SUCCESS",
      message: "Query executed successfully",
      data: [{ item: "Item-1", revenue: 5000 }],
      columns: ["item", "revenue"],
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockApproveResponse,
    });

    const req: ApprovalRequest = {
      session_id: "sess_hitl",
      approved: true,
    };

    const result = await approveQuery(req, "admin-secret-token");

    expect(result.approved).toBe(true);
    expect(result.status).toBe("SUCCESS");

    const [url, options] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/query/approve");
    expect(options.headers["X-User-Role"]).toBe("Admin");
    expect(options.headers["X-Admin-Token"]).toBe("admin-secret-token");
  });
});
