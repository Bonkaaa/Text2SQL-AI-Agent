/**
 * TypeScript Interfaces & Types cho Frontend Text2SQL AI Agent.
 * Khớp chuẩn 100% với Pydantic Schemas trong src/models/api_schemas.py và src/models/state.py.
 */

// ==============================================================================
// 1. NGƯỜI DÙNG & PHÂN QUYỀN (RBAC)
// ==============================================================================

export type UserRole = "Analyst" | "Admin";

export interface UserProfile {
  id: string;
  name: string;
  role: UserRole;
  avatarUrl?: string;
}

// ==============================================================================
// 2. TRẠNG THÁI PHẢN HỒI CỦA AI AGENT
// ==============================================================================

export type QueryStatus =
  | "COMPLETED"
  | "CLARIFICATION_REQUIRED"
  | "PENDING_APPROVAL"
  | "ERROR"
  | "EXECUTION_FAILED";

// ==============================================================================
// 3. CẤU HÌNH TRỰC QUAN HÓA BIỂU ĐỒ (RECHARTS CONFIG)
// ==============================================================================

export type ChartType = "bar" | "line" | "area" | "pie" | "table";

export interface RechartsConfig {
  chart_type: ChartType;
  title?: string;
  x_key?: string;
  x_axis?: string;
  y_keys?: string[];
  y_axis?: string[] | string;
  series_labels?: Record<string, string>;
  description?: string;
  legend?: boolean;
}

// ==============================================================================
// 4. API ENDPOINT: /api/v1/query/ask
// ==============================================================================

export interface AskQueryRequest {
  question: string;
  session_id?: string | null;
  user_id?: string;
  role?: UserRole;
}

export interface QueryResponse {
  session_id: string;
  status: QueryStatus;
  question: string;
  is_ambiguous: boolean;
  clarification_question?: string | null;
  suggested_options: string[];
  final_answer?: string | null;
  sql?: string | null;
  data?: Record<string, any>[] | null;
  columns?: string[] | null;
  recharts_config?: RechartsConfig | null;
  requires_hitl: boolean;
  estimated_cost_bytes?: number | null;
  execution_time_ms: number;
  error?: string | null;
  error_type?: string | null;
  retry_count?: number | null;
}

// ==============================================================================
// 5. API ENDPOINT: /api/v1/query/approve (HITL)
// ==============================================================================

export interface ApprovalRequest {
  session_id: string;
  approved: boolean;
  rejection_reason?: string | null;
}

export interface ApprovalResponse {
  session_id: string;
  approved: boolean;
  status: string;
  message: string;
  data?: Record<string, any>[] | null;
  columns?: string[] | null;
}

// ==============================================================================
// 6. API ENDPOINT: /api/v1/query/history
// ==============================================================================

export interface QueryHistoryItem {
  session_id: string;
  timestamp?: string | null;
  status?: string | null;
  question?: string | null;
  artifacts: string[];
}

export interface QueryHistoryResponse {
  session_id: string;
  history: QueryHistoryItem[];
}

// ==============================================================================
// 7. API ENDPOINT: /api/v1/audit/logs (ADMIN ONLY)
// ==============================================================================

export interface AuditLogItem {
  timestamp?: string;
  created_at?: string;
  query_id?: string;
  trace_id?: string;
  session_id: string;
  user_id: string;
  role: string;
  event_type?: string;
  question?: string;
  sql?: string;
  status: string;
  execution_time_ms: number;
  bytes_scanned?: number;
  error_type?: string;
  error_message?: string;
  tables_used?: string[];
  columns_used?: string[];
}

export interface AuditLogsResponse {
  total: number;
  limit: number;
  offset: number;
  logs: AuditLogItem[];
}

// ==============================================================================
// 8. API ENDPOINT: /health & /api/v1/health
// ==============================================================================

export interface HealthResponse {
  status: string;
  database: string;
  version: string;
}

// ==============================================================================
// 9. CLIENT-SIDE CHAT STATE (MESSAGE FEED DATA STRUCTURE)
// ==============================================================================

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  // Trạng thái mở rộng cho phản hồi của Assistant
  status?: QueryStatus;
  queryResponse?: QueryResponse;
  isLoading?: boolean;
}
