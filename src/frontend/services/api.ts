/**
 * API Client & Network Service Layer cho Frontend Text2SQL AI Agent.
 * Kết nối với FastAPI Backend Gateway (mặc định: http://localhost:8000).
 */

import {
  ApprovalRequest,
  ApprovalResponse,
  AskQueryRequest,
  AuditLogsResponse,
  HealthResponse,
  QueryHistoryResponse,
  QueryResponse,
  UserRole,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SESSION_TOKENS_STORAGE_KEY = "text2sql_session_tokens";

export function getSessionToken(sessionId?: string): string | null {
  if (typeof window === "undefined" || !sessionId) return null;
  try {
    const raw = localStorage.getItem(SESSION_TOKENS_STORAGE_KEY);
    if (!raw) return null;
    const map = JSON.parse(raw);
    return map[sessionId] || null;
  } catch {
    return null;
  }
}

export function saveSessionToken(sessionId?: string, token?: string): void {
  if (typeof window === "undefined" || !sessionId || !token) return;
  try {
    const raw = localStorage.getItem(SESSION_TOKENS_STORAGE_KEY);
    const map = raw ? JSON.parse(raw) : {};
    map[sessionId] = token;
    localStorage.setItem(SESSION_TOKENS_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore
  }
}

/**
 * Lớp lỗi chuẩn hóa cho các yêu cầu API.
 */
export class ApiError extends Error {
  public statusCode?: number;
  public details?: any;

  constructor(message: string, statusCode?: number, details?: any) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Hàm hỗ trợ gửi HTTP request với xử lý lỗi mạng và timeout tập trung.
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs: number = 60000
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers as Record<string, string>),
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Lưu token nếu backend trả về trong header
    const tokenHeader =
      response.headers.get("x-session-token") ||
      response.headers.get("X-Session-Token");

    // Xử lý phản hồi không thành công
    if (!response.ok) {
      let errorDetail = "";
      try {
        const errorJson = await response.json();
        errorDetail =
          errorJson.detail || errorJson.error || JSON.stringify(errorJson);
      } catch {
        errorDetail = await response.text();
      }

      // Chuẩn hóa thông báo lỗi theo mã trạng thái HTTP
      let friendlyMessage = `Lỗi máy chủ (${response.status}): ${errorDetail}`;
      if (response.status === 403) {
        friendlyMessage = `Quyền truy cập bị từ chối: ${errorDetail || "Bạn không có quyền thực hiện thao tác này."}`;
      } else if (response.status === 404) {
        friendlyMessage = `Không tìm thấy tài nguyên yêu cầu (404).`;
      } else if (response.status === 422) {
        friendlyMessage = `Dữ liệu gửi lên không hợp lệ: ${errorDetail}`;
      } else if (response.status >= 500) {
        friendlyMessage = `Lỗi máy chủ nội bộ (${response.status}): ${errorDetail || "Vui lòng thử lại sau."}`;
      }

      throw new ApiError(friendlyMessage, response.status, errorDetail);
    }

    const data = (await response.json()) as T;
    const returnedSessionId = (data as any)?.session_id;
    const tokenToSave = tokenHeader || (data as any)?.session_token;
    if (returnedSessionId && tokenToSave) {
      saveSessionToken(returnedSessionId, tokenToSave);
    }

    return data;
  } catch (error: any) {
    clearTimeout(timeoutId);

    if (error instanceof ApiError) {
      throw error;
    }

    if (error.name === "AbortError") {
      throw new ApiError(
        `Quá thời gian phản hồi từ máy chủ (${timeoutMs / 1000} giây). Truy vấn có thể đang xử lý phức tạp.`,
        408
      );
    }

    // Lỗi mất kết nối mạng hoặc không thể kết nối tới backend
    throw new ApiError(
      `Không thể kết nối đến máy chủ backend tại ${API_BASE_URL}. Vui lòng kiểm tra lại dịch vụ FastAPI.`,
      0,
      error.message
    );
  }
}

export function getCurrentStoredRole(): UserRole {
  if (typeof window === "undefined") return "Analyst";
  try {
    const raw = localStorage.getItem("text2sql_user_role");
    if (raw && raw.toLowerCase() === "admin") return "Admin";
  } catch {
    // Ignore
  }
  return "Analyst";
}

// ==============================================================================
// CÁC HÀM GỌI API CHÍNH
// ==============================================================================

/**
 * 1. Gửi câu hỏi phân tích dữ liệu tự nhiên tới Deep Agent Supervisor.
 * Endpoint: POST /api/v1/query/ask
 */
export async function askQuery(
  request: AskQueryRequest,
  role?: UserRole
): Promise<QueryResponse> {
  const token = request.session_id ? getSessionToken(request.session_id) : null;
  const activeRole = role || request.role || getCurrentStoredRole();
  const headers: Record<string, string> = {
    "X-User-Role": activeRole,
  };
  if (token) {
    headers["X-Session-Token"] = token;
    if (!request.session_token) {
      request.session_token = token;
    }
  }

  return apiFetch<QueryResponse>("/api/v1/query/ask", {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });
}

/**
 * 2. Gửi quyết định phê duyệt hoặc từ chối câu truy vấn chờ duyệt HITL.
 * Endpoint: POST /api/v1/query/approve
 */
export async function approveQuery(
  request: ApprovalRequest,
  role?: UserRole
): Promise<ApprovalResponse> {
  const token = request.session_id ? getSessionToken(request.session_id) : null;
  const activeRole = role || getCurrentStoredRole();
  const headers: Record<string, string> = {
    "X-User-Role": activeRole,
  };
  if (token) {
    headers["X-Session-Token"] = token;
  }

  return apiFetch<ApprovalResponse>("/api/v1/query/approve", {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });
}

/**
 * 3. Lấy lịch sử danh sách artifacts và trạng thái truy vấn của một phiên.
 * Endpoint: GET /api/v1/query/history?session_id=...
 */
export async function getQueryHistory(
  sessionId: string,
  role?: UserRole
): Promise<QueryHistoryResponse> {
  const encodedSessionId = encodeURIComponent(sessionId);
  const token = getSessionToken(sessionId);
  const activeRole = role || getCurrentStoredRole();
  const headers: Record<string, string> = {
    "X-User-Role": activeRole,
  };
  if (token) {
    headers["X-Session-Token"] = token;
  }
  return apiFetch<QueryHistoryResponse>(
    `/api/v1/query/history?session_id=${encodedSessionId}`,
    {
      method: "GET",
      headers,
    }
  );
}

/**
 * 4. Truy vấn nhật ký kiểm toán hệ thống (Audit Logs) - Yêu cầu vai trò ADMIN.
 * Endpoint: GET /api/v1/audit/logs
 */
export async function getAuditLogs(
  limit: number = 50,
  offset: number = 0,
  role: UserRole = "Admin"
): Promise<AuditLogsResponse> {
  return apiFetch<AuditLogsResponse>(
    `/api/v1/audit/logs?limit=${limit}&offset=${offset}`,
    {
      method: "GET",
      headers: {
        "X-User-Role": role,
      },
    }
  );
}

/**
 * 5. Kiểm tra tình trạng hoạt động của Backend Gateway và DuckDB Database.
 * Endpoint: GET /health
 */
export async function checkBackendHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", {
    method: "GET",
  }, 5000); // 5 giây timeout cho health check
}
