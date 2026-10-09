"use client";

import { useState, useCallback, useRef } from "react";
import { QueryResponse, UserRole } from "@/types/api";
import { askQuery, approveQuery } from "@/lib/api-client";

export interface WorkspaceMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  status?: "COMPLETED" | "SUCCESS" | "CLARIFICATION_REQUIRED" | "PENDING_APPROVAL" | "SECURITY_BLOCKED" | "ERROR";
  queryResponse?: QueryResponse;
  isLoading?: boolean;
}

export type ResultTabType = "answer" | "table" | "chart" | "sql" | "trace";

export function useWorkspace() {
  const [messages, setMessages] = useState<WorkspaceMessage[]>([]);
  const [activeTab, setActiveTab] = useState<ResultTabType>("chart");
  const [isLoading, setIsLoading] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<QueryResponse | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => `sess_${Math.random().toString(36).substring(2, 10)}`);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const sessionTokenRef = useRef(sessionToken);
  sessionTokenRef.current = sessionToken;

  const submitQuery = useCallback(async (question: string, role: UserRole = "Analyst") => {
    if (!question.trim()) return;

    const userMsgId = `msg_user_${Date.now()}`;
    const asstMsgId = `msg_asst_${Date.now()}`;
    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const newUserMsg: WorkspaceMessage = {
      id: userMsgId,
      role: "user",
      content: question,
      timestamp,
    };

    const newAsstMsg: WorkspaceMessage = {
      id: asstMsgId,
      role: "assistant",
      content: "",
      timestamp,
      isLoading: true,
    };

    setMessages((prev) => [...prev, newUserMsg, newAsstMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await askQuery(
        {
          question,
          session_id: sessionIdRef.current,
          session_token: sessionTokenRef.current || undefined,
          role,
        },
        sessionTokenRef.current || undefined
      );

      if (response.session_token) {
        setSessionToken(response.session_token);
      }

      setCurrentResponse(response);

      // Auto-select tab logic
      const hasChart =
        response.recharts_config ||
        response.response_package?.artifacts?.some((a) => a.type === "chart");
      const hasTable =
        (response.data && response.data.length > 0) ||
        response.response_package?.artifacts?.some((a) => a.type === "table");

      if (hasChart) {
        setActiveTab("chart");
      } else if (hasTable) {
        setActiveTab("table");
      } else {
        setActiveTab("answer");
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === asstMsgId
            ? {
                ...msg,
                isLoading: false,
                content:
                  response.final_answer ||
                  response.response_package?.direct_answer ||
                  (response.status === "CLARIFICATION_REQUIRED"
                    ? response.clarification_question || "Vui lòng làm rõ câu hỏi."
                    : response.status === "PENDING_APPROVAL"
                    ? "Truy vấn cần được quản trị viên phê duyệt trước khi thực thi."
                    : response.status === "SECURITY_BLOCKED"
                    ? response.refusal_reason || "Yêu cầu bị từ chối do chính sách bảo mật."
                    : "Đã xử lý xong câu hỏi."),
                status: response.status,
                queryResponse: response,
              }
            : msg
        )
      );
    } catch (err: any) {
      const errorMsg = err.message || "Lỗi kết nối máy chủ phân tích.";
      setError(errorMsg);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === asstMsgId
            ? {
                ...msg,
                isLoading: false,
                content: errorMsg,
                status: "ERROR",
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const approveHitl = useCallback(
    async (approved: boolean, reason?: string, adminToken?: string) => {
      setIsApproving(true);
      setError(null);
      try {
        const res = await approveQuery(
          {
            session_id: sessionIdRef.current,
            session_token: sessionTokenRef.current || undefined,
            approved,
            rejection_reason: reason,
          },
          adminToken
        );

        setMessages((prev) => {
          const updated = [...prev];
          const lastAsstIdx = updated.findLastIndex(
            (m) =>
              m.role === "assistant" &&
              (m.status === "PENDING_APPROVAL" || m.queryResponse?.requires_hitl)
          );
          if (lastAsstIdx !== -1) {
            const target = updated[lastAsstIdx];
            updated[lastAsstIdx] = {
              ...target,
              status: approved ? "COMPLETED" : "ERROR",
              content: res.message || (approved ? "Đã phê duyệt thành công." : "Đã từ chối truy vấn."),
              queryResponse: target.queryResponse
                ? {
                    ...target.queryResponse,
                    status: approved ? "COMPLETED" : "ERROR",
                    requires_hitl: false,
                    data: res.data || target.queryResponse.data,
                    columns: res.columns || target.queryResponse.columns,
                  }
                : undefined,
            };
          }
          return updated;
        });

        if (approved && res.data) {
          setCurrentResponse((prev) =>
            prev
              ? {
                  ...prev,
                  status: "COMPLETED",
                  requires_hitl: false,
                  data: res.data,
                  columns: res.columns,
                }
              : null
          );
          setActiveTab("table");
        }
      } catch (err: any) {
        setError(err.message || "Lỗi phê duyệt truy vấn.");
      } finally {
        setIsApproving(false);
      }
    },
    []
  );

  const selectClarificationOption = useCallback(
    async (option: string) => {
      await submitQuery(option);
    },
    [submitQuery]
  );

  const resetConversation = useCallback(() => {
    setMessages([]);
    setCurrentResponse(null);
    setError(null);
    setActiveTab("chart");
    const newId = `sess_${Math.random().toString(36).substring(2, 10)}`;
    setSessionId(newId);
    setSessionToken(null);
  }, []);

  return {
    messages,
    activeTab,
    setActiveTab,
    isLoading,
    isApproving,
    currentResponse,
    sessionId,
    error,
    submitQuery,
    approveHitl,
    selectClarificationOption,
    resetConversation,
  };
}
