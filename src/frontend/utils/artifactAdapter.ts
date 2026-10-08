import type { QueryResponse } from "../types/api";
import type {
  ArtifactItem,
  ChartArtifact,
  TableArtifact,
  CalloutArtifact,
  ExtractedArtifactsResult,
} from "../types/artifacts";

/**
 * Adapter chuẩn hóa dữ liệu phản hồi từ backend thành mảng ArtifactItem định kiểu.
 * Hỗ trợ song song cả ResponsePackage mới (v4.0) và Legacy flat payload (v1-v3).
 */
export function extractArtifactsFromResponse(
  response: QueryResponse
): ExtractedArtifactsResult {
  // 1. Ưu tiên cao nhất: ResponsePackage hoàn chỉnh từ backend
  if (response.response_package) {
    const pkg = response.response_package;
    return {
      artifacts: pkg.artifacts || [],
      layout: pkg.layout || "stacked",
      directAnswer: pkg.direct_answer,
      detailedInsight: pkg.detailed_insight,
    };
  }

  // 2. Ưu tiên 2: Mảng output_artifacts đã có sẵn
  if (response.output_artifacts && response.output_artifacts.length > 0) {
    return {
      artifacts: response.output_artifacts,
      layout: "stacked",
      directAnswer: response.final_answer || undefined,
    };
  }

  // 3. Xử lý trạng thái lỗi (ERROR hoặc EXECUTION_FAILED)
  if (response.status === "ERROR" || response.status === "EXECUTION_FAILED" || response.error) {
    const errorCallout: CalloutArtifact = {
      type: "callout",
      variant: "error",
      message: response.error || "Truy vấn cơ sở dữ liệu đã bị gián đoạn hoặc gặp lỗi thực thi.",
    };
    return {
      artifacts: [errorCallout],
      layout: "stacked",
      directAnswer: response.final_answer || undefined,
    };
  }

  // 4. Xử lý tập dữ liệu rỗng (No data)
  if (Array.isArray(response.data) && response.data.length === 0) {
    const noDataCallout: CalloutArtifact = {
      type: "callout",
      variant: "no_data",
      message: "Không tìm thấy dữ liệu phù hợp với điều kiện truy vấn đã chỉ định.",
    };
    return {
      artifacts: [noDataCallout],
      layout: "stacked",
      directAnswer: response.final_answer || undefined,
    };
  }

  // 5. Fallback cho legacy flat response (recharts_config + data + columns)
  const legacyArtifacts: ArtifactItem[] = [];

  if (Array.isArray(response.data) && response.data.length > 0) {
    // 5a. Tạo ChartArtifact nếu có cấu hình biểu đồ
    if (response.recharts_config) {
      const cfg = response.recharts_config;
      const chartType = (cfg.chart_type === "table" ? "bar" : cfg.chart_type) as ChartArtifact["chart_type"];
      const xKey = cfg.x_key || cfg.x_axis || Object.keys(response.data[0])[0] || "category";

      let yKeys: string[] = [];
      if (Array.isArray(cfg.y_keys) && cfg.y_keys.length > 0) {
        yKeys = cfg.y_keys;
      } else if (Array.isArray(cfg.y_axis) && cfg.y_axis.length > 0) {
        yKeys = cfg.y_axis;
      } else if (typeof cfg.y_axis === "string") {
        yKeys = [cfg.y_axis];
      } else {
        const potentialKeys = Object.keys(response.data[0]).filter((k) => k !== xKey);
        yKeys = potentialKeys.length > 0 ? [potentialKeys[0]] : ["value"];
      }

      legacyArtifacts.push({
        type: "chart",
        chart_type: chartType,
        title: cfg.title || "Biểu đồ trực quan hóa dữ liệu",
        x_key: xKey,
        y_keys: yKeys,
        series_labels: cfg.series_labels || {},
        data: response.data,
      });
    }

    // 5b. Tạo TableArtifact nếu có dữ liệu bảng
    const columns =
      Array.isArray(response.columns) && response.columns.length > 0
        ? response.columns
        : Object.keys(response.data[0] || {});

    legacyArtifacts.push({
      type: "table",
      title: "Bảng dữ liệu chi tiết",
      columns,
      rows: response.data,
      total_row_count: response.data.length,
    });
  }

  return {
    artifacts: legacyArtifacts,
    layout: "stacked",
    directAnswer: response.final_answer || undefined,
  };
}
