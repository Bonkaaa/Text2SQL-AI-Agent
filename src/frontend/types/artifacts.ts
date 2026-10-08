/**
 * TypeScript Interfaces & Types cho Multi-Artifact Presentation Engine.
 * Khớp chuẩn 100% với Pydantic v2 Models trong src/models/artifacts.py.
 */

// ==============================================================================
// 1. CÁC PRIMITIVE ARTIFACTS (DISCRIMINATED BY "type")
// ==============================================================================

export type ArtifactType =
  | "kpi"
  | "chart"
  | "table"
  | "evidence"
  | "callout"
  | "file";

/**
 * 1. Thẻ chỉ số số liệu định lượng (cho câu hỏi đơn hoặc chỉ số tài chính quan trọng)
 */
export interface KpiArtifact {
  type: "kpi";
  title: string;
  value: number | string;
  unit?: string | null;
  delta?: number | null;
  delta_type?: "increase" | "decrease" | "neutral" | null;
}

/**
 * 2. Biểu đồ trực quan hóa Recharts hoàn chỉnh kèm mảng data đã hydrate
 */
export interface ChartArtifact {
  type: "chart";
  chart_type: "bar" | "line" | "area" | "pie" | "composed";
  title: string;
  x_key: string;
  y_keys: string[];
  series_labels?: Record<string, string>;
  data: Record<string, any>[];
  color_palette?: string[];
}

/**
 * 3. Bảng số liệu chi tiết kèm metadata định dạng cột
 */
export interface TableArtifact {
  type: "table";
  title: string;
  columns: string[];
  column_formats?: Record<string, string>;
  rows: Record<string, any>[];
  total_row_count: number;
}

/**
 * 4. Dẫn chứng liên kết luận điểm nhận định với câu SQL và mẫu số liệu
 */
export interface EvidenceArtifact {
  type: "evidence";
  task_id: string;
  claim: string;
  supporting_sql: string;
  sample_values?: Record<string, any>[];
}

/**
 * 5. Cảnh báo, thông tin lưu ý hoặc thông báo không có dữ liệu
 */
export interface CalloutArtifact {
  type: "callout";
  variant: "info" | "warning" | "error" | "no_data";
  message: string;
}

/**
 * 6. Tệp tin xuất xưởng cho phép tải về
 */
export interface FileArtifact {
  type: "file";
  file_name: string;
  file_type: "csv" | "xlsx" | "json";
  download_url: string;
}

/**
 * Tagged / Discriminated Union cho toàn bộ Artifacts
 */
export type ArtifactItem =
  | KpiArtifact
  | ChartArtifact
  | TableArtifact
  | EvidenceArtifact
  | CalloutArtifact
  | FileArtifact;

// ==============================================================================
// 2. RESPONSE PACKAGE TỪ BACKEND
// ==============================================================================

export type ArtifactLayout = "focus" | "stacked" | "dashboard_grid";

export interface ExecutedQueryInfo {
  task_id: string;
  sql: string;
}

export interface ResponsePackage {
  session_id: string;
  direct_answer: string;
  detailed_insight?: string[];
  layout: ArtifactLayout;
  artifacts: ArtifactItem[];
  executed_queries?: ExecutedQueryInfo[];
  total_execution_time_ms?: number;
}

export interface ExtractedArtifactsResult {
  artifacts: ArtifactItem[];
  layout: ArtifactLayout;
  directAnswer?: string;
  detailedInsight?: string[];
}
