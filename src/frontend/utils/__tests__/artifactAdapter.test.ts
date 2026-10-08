import { describe, it, expect } from "vitest";
import { extractArtifactsFromResponse } from "../artifactAdapter";
import type { QueryResponse } from "../../types/api";
import type { ResponsePackage, ArtifactItem } from "../../types/artifacts";

describe("artifactAdapter - extractArtifactsFromResponse", () => {
  it("should extract artifacts directly when response_package is present", () => {
    const mockPackage: ResponsePackage = {
      session_id: "sess_123",
      direct_answer: "Doanh thu năm 2002 đạt 12.5 triệu USD.",
      detailed_insight: [
        "Kênh Store Sales đóng góp 62% tổng doanh thu.",
        "Mặt hàng Electronics có biên lợi nhuận cao nhất (24.5%).",
      ],
      layout: "dashboard_grid",
      artifacts: [
        {
          type: "kpi",
          title: "Net Paid Sales",
          value: 12500000,
          unit: "USD",
          delta: 14.2,
          delta_type: "increase",
        },
        {
          type: "chart",
          chart_type: "bar",
          title: "Doanh thu theo kênh",
          x_key: "channel",
          y_keys: ["revenue"],
          series_labels: { revenue: "Doanh thu" },
          data: [
            { channel: "Store", revenue: 7750000 },
            { channel: "Web", revenue: 3100000 },
            { channel: "Catalog", revenue: 1650000 },
          ],
        },
        {
          type: "table",
          title: "Chi tiết doanh thu và lợi nhuận",
          columns: ["channel", "revenue", "profit"],
          column_formats: { revenue: "currency", profit: "currency" },
          rows: [
            { channel: "Store", revenue: 7750000, profit: 1240000 },
            { channel: "Web", revenue: 3100000, profit: 450000 },
          ],
          total_row_count: 2,
        },
      ],
      executed_queries: [{ task_id: "task_1", sql: "SELECT * FROM store_sales" }],
      total_execution_time_ms: 142.5,
    };

    const response: QueryResponse = {
      session_id: "sess_123",
      status: "COMPLETED",
      question: "Tổng doanh thu năm 2002 là bao nhiêu?",
      is_ambiguous: false,
      suggested_options: [],
      execution_time_ms: 142.5,
      requires_hitl: false,
      response_package: mockPackage,
    };

    const result = extractArtifactsFromResponse(response);

    expect(result.artifacts).toHaveLength(3);
    expect(result.layout).toBe("dashboard_grid");
    expect(result.directAnswer).toBe("Doanh thu năm 2002 đạt 12.5 triệu USD.");
    expect(result.detailedInsight).toHaveLength(2);

    expect(result.artifacts[0].type).toBe("kpi");
    expect(result.artifacts[1].type).toBe("chart");
    expect(result.artifacts[2].type).toBe("table");
  });

  it("should extract artifacts when output_artifacts array is provided", () => {
    const mockArtifacts: ArtifactItem[] = [
      {
        type: "evidence",
        task_id: "task_1",
        claim: "Top 1 khách hàng có số lần mua nhiều nhất",
        supporting_sql: "SELECT c_customer_id, count(*) FROM store_sales ...",
        sample_values: [{ c_customer_id: "CUST_001", count: 42 }],
      },
    ];

    const response: QueryResponse = {
      session_id: "sess_456",
      status: "COMPLETED",
      question: "Ai là khách hàng trung thành nhất?",
      is_ambiguous: false,
      suggested_options: [],
      execution_time_ms: 80,
      requires_hitl: false,
      output_artifacts: mockArtifacts,
    };

    const result = extractArtifactsFromResponse(response);

    expect(result.artifacts).toHaveLength(1);
    expect(result.artifacts[0].type).toBe("evidence");
    expect(result.layout).toBe("stacked");
  });

  it("should fallback cleanly for legacy flat response (recharts_config + data + columns)", () => {
    const legacyResponse: QueryResponse = {
      session_id: "sess_legacy",
      status: "COMPLETED",
      question: "So sánh doanh thu Store vs Web",
      is_ambiguous: false,
      suggested_options: [],
      final_answer: "Store sales cao gấp đôi Web sales.",
      execution_time_ms: 120,
      requires_hitl: false,
      columns: ["channel", "sales"],
      data: [
        { channel: "Store", sales: 1000 },
        { channel: "Web", sales: 500 },
      ],
      recharts_config: {
        chart_type: "bar",
        title: "Doanh số theo kênh",
        x_key: "channel",
        y_keys: ["sales"],
        series_labels: { sales: "Doanh số" },
      },
    };

    const result = extractArtifactsFromResponse(legacyResponse);

    expect(result.artifacts).toHaveLength(2);
    // 1st should be ChartArtifact
    expect(result.artifacts[0].type).toBe("chart");
    const chart = result.artifacts[0] as any;
    expect(chart.title).toBe("Doanh số theo kênh");
    expect(chart.data).toEqual(legacyResponse.data);

    // 2nd should be TableArtifact
    expect(result.artifacts[1].type).toBe("table");
    const table = result.artifacts[1] as any;
    expect(table.columns).toEqual(["channel", "sales"]);
    expect(table.rows).toEqual(legacyResponse.data);
    expect(table.total_row_count).toBe(2);

    expect(result.directAnswer).toBe("Store sales cao gấp đôi Web sales.");
  });

  it("should create CalloutArtifact when response has error", () => {
    const errorResponse: QueryResponse = {
      session_id: "sess_err",
      status: "ERROR",
      question: "Lỗi syntax SQL",
      is_ambiguous: false,
      suggested_options: [],
      execution_time_ms: 10,
      requires_hitl: false,
      error: "Bảng không tồn tại: store_sales_invalid",
    };

    const result = extractArtifactsFromResponse(errorResponse);

    expect(result.artifacts).toHaveLength(1);
    expect(result.artifacts[0].type).toBe("callout");
    const callout = result.artifacts[0] as any;
    expect(callout.variant).toBe("error");
    expect(callout.message).toContain("store_sales_invalid");
  });

  it("should handle empty or no-data responses gracefully", () => {
    const emptyResponse: QueryResponse = {
      session_id: "sess_empty",
      status: "COMPLETED",
      question: "Truy vấn không trả về kết quả",
      is_ambiguous: false,
      suggested_options: [],
      execution_time_ms: 50,
      requires_hitl: false,
      data: [],
      columns: ["id", "val"],
    };

    const result = extractArtifactsFromResponse(emptyResponse);

    expect(result.artifacts).toHaveLength(1);
    expect(result.artifacts[0].type).toBe("callout");
    const callout = result.artifacts[0] as any;
    expect(callout.variant).toBe("no_data");
  });
});
