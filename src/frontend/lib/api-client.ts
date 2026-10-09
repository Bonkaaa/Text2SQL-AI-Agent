import { AskQueryRequest, ApprovalRequest, ApprovalResponse, QueryResponse } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getStoredAuth() {
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem("querypilot_auth_user");
      if (stored) return JSON.parse(stored);
    } catch {
      // Ignore storage errors
    }
  }
  return null;
}

export async function askQuery(
  request: AskQueryRequest,
  sessionToken?: string
): Promise<QueryResponse> {
  const auth = getStoredAuth();
  const url = `${API_BASE_URL}/api/v1/query/ask`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-User-Id": request.user_id || auth?.id || "analyst_alex",
    "X-User-Role": request.role || auth?.role || "Analyst",
    "X-Session-Id": request.session_id || "default_session",
  };

  const token = sessionToken || request.session_token;
  if (token) {
    headers["X-Session-Token"] = token;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let errorDetail = "Failed to communicate with QueryPilot backend";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.error || errorDetail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }

  const data: QueryResponse = await response.json();
  return data;
}

export async function approveQuery(
  request: ApprovalRequest,
  adminToken?: string
): Promise<ApprovalResponse> {
  const auth = getStoredAuth();
  const url = `${API_BASE_URL}/api/v1/query/approve`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-User-Role": auth?.role || "Admin",
    "X-Session-Id": request.session_id,
  };

  const effectiveAdminToken =
    adminToken || auth?.adminToken || (auth?.role === "Admin" ? "admin_secret_token_2026" : undefined);
  if (effectiveAdminToken) {
    headers["X-Admin-Token"] = effectiveAdminToken;
  }
  if (request.session_token) {
    headers["X-Session-Token"] = request.session_token;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let errorDetail = "Failed to process HITL approval";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.error || errorDetail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }

  const data: ApprovalResponse = await response.json();
  return data;
}
