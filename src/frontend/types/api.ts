export type UserRole = "Analyst" | "Admin" | "Business_User";

export interface AskQueryRequest {
  question: string;
  session_id?: string;
  user_id?: string;
  role?: UserRole;
  session_token?: string;
}

export interface ApprovalRequest {
  session_id: string;
  task_id?: string;
  approval_id?: string;
  session_token?: string;
  approved: boolean;
  rejection_reason?: string;
}

export interface ApprovalResponse {
  session_id: string;
  approval_id?: string;
  approved: boolean;
  status: string;
  message: string;
  session_token?: string;
  data?: Record<string, any>[];
  columns?: string[];
}

export interface KpiArtifact {
  type: "kpi";
  title: string;
  value: number | string;
  unit?: string;
  delta?: number;
  delta_type?: "increase" | "decrease" | "neutral";
}

export interface ChartArtifact {
  type: "chart";
  chart_type: "bar" | "line" | "area" | "pie" | "composed";
  title: string;
  x_key: string;
  y_keys: string[];
  series_labels?: Record<string, string>;
  data: Record<string, any>[];
}

export interface TableArtifact {
  type: "table";
  title: string;
  columns: string[];
  column_formats?: Record<string, string>;
  rows: Record<string, any>[];
  total_row_count?: number;
}

export interface EvidenceArtifact {
  type: "evidence";
  task_id: string;
  claim: string;
  supporting_sql: string;
  sample_values?: Record<string, any>[];
}

export interface CalloutArtifact {
  type: "callout";
  variant: "info" | "warning" | "error" | "no_data";
  message: string;
}

export interface FileArtifact {
  type: "file";
  file_name: string;
  file_type: string;
  download_url: string;
}

export type ArtifactItem =
  | KpiArtifact
  | ChartArtifact
  | TableArtifact
  | EvidenceArtifact
  | CalloutArtifact
  | FileArtifact;

export interface ResponsePackage {
  session_id: string;
  direct_answer: string;
  detailed_insight?: string[];
  layout?: "focus" | "stacked" | "dashboard_grid";
  artifacts: ArtifactItem[];
  executed_queries?: { task_id: string; sql: string }[];
  total_execution_time_ms?: number;
}

export interface QueryArtifact {
  artifact_id: string;
  task_id: string;
  sql: string;
  dialect: string;
  explanation?: string;
  tables_used?: string[];
  columns_used?: string[];
  status: string;
  data?: Record<string, any>[];
  columns?: string[];
  row_count?: number;
  execution_time_ms?: number;
  error_message?: string;
}

export interface AnalysisTask {
  task_id: string;
  description: string;
  status: string;
  query_artifact?: QueryArtifact;
  retry_count?: number;
}

export interface QueryResponse {
  session_id: string;
  status:
    | "COMPLETED"
    | "SUCCESS"
    | "CLARIFICATION_REQUIRED"
    | "SECURITY_BLOCKED"
    | "PENDING_APPROVAL"
    | "ERROR";
  question: string;
  final_answer?: string;
  response_package?: ResponsePackage;
  output_artifacts?: ArtifactItem[];
  sql?: string;
  data?: Record<string, any>[];
  columns?: string[];
  recharts_config?: any;
  insight?: any;
  visualization?: any;
  is_safe?: boolean;
  safety_category?: string;
  refusal_reason?: string;
  is_ambiguous?: boolean;
  clarification_question?: string;
  suggested_options?: string[];
  tasks?: AnalysisTask[];
  artifacts?: QueryArtifact[];
  requires_hitl?: boolean;
  estimated_cost_bytes?: number;
  execution_time_ms?: number;
  error?: string;
  session_token?: string;
}
