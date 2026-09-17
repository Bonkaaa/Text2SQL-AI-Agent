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

    return (await response.json()) as T;
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

// ==============================================================================
// CÁC HÀM GỌI API CHÍNH
// ==============================================================================

/**
 * 1. Gửi câu hỏi phân tích dữ liệu tự nhiên tới Deep Agent Supervisor.
 * Endpoint: POST /api/v1/query/ask
 */
export async function askQuery(
  request: AskQueryRequest
): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/api/v1/query/ask", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/**
 * 2. Gửi quyết định phê duyệt hoặc từ chối câu truy vấn chờ duyệt HITL.
 * Endpoint: POST /api/v1/query/approve
 */
export async function approveQuery(
  request: ApprovalRequest
): Promise<ApprovalResponse> {
  return apiFetch<ApprovalResponse>("/api/v1/query/approve", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/**
 * 3. Lấy lịch sử danh sách artifacts và trạng thái truy vấn của một phiên.
 * Endpoint: GET /api/v1/query/history?session_id=...
 */
export async function getQueryHistory(
  sessionId: string
): Promise<QueryHistoryResponse> {
  const encodedSessionId = encodeURIComponent(sessionId);
  return apiFetch<QueryHistoryResponse>(
    `/api/v1/query/history?session_id=${encodedSessionId}`,
    {
      method: "GET",
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
  role: UserRole = "ADMIN"
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
