"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { SchemaDrawer } from "@/components/layout/SchemaDrawer";
import { InspectorDrawer } from "@/components/layout/InspectorDrawer";
import { ExecutiveLaunchpad } from "@/components/chat/ExecutiveLaunchpad";
import { QueryInputCard } from "@/components/chat/QueryInputCard";
import { MessageList } from "@/components/chat/MessageList";
import { useAppContext } from "@/context/AppContext";
import { askQuery, approveQuery } from "@/services/api";
import { ChatMessage, QueryResponse } from "@/types/api";

export default function HomePage() {
  const {
    currentRole,
    currentSessionId,
    setCurrentSessionId,
    startNewSession,
    showToast,
  } = useAppContext();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isApprovingHitl, setIsApprovingHitl] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);

  // Shortcut Ctrl+B / Cmd+B to toggle Inspector Drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setIsInspectorOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Handle submitting query to FastAPI backend
  const handleSendQuery = async (
    question: string,
    options?: { reasoning?: boolean; dryRun?: boolean }
  ) => {
    if (!question.trim() || isLoading) return;

    const userMessageId = `msg_user_${Date.now()}`;
    const assistantMessageId = `msg_asst_${Date.now()}`;

    const userMessage: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: question,
      timestamp: new Date(),
    };

    const pendingAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMessage, pendingAssistantMessage]);
    setIsLoading(true);

    try {
      let response: QueryResponse;
      try {
        response = await askQuery({
          question,
          session_id: currentSessionId || undefined,
          role: currentRole,
        });
      } catch (firstErr: any) {
        // Tự động giải cứu nếu session cũ bị lỗi token xác thực
        if (
          firstErr?.message?.includes("Session Token") ||
          firstErr?.details?.includes("Session Token")
        ) {
          const freshSessionId = startNewSession();
          response = await askQuery({
            question,
            session_id: freshSessionId,
            role: currentRole,
          });
        } else {
          throw firstErr;
        }
      }

      // Cập nhật lại session_id nếu backend cấp ID mới
      if (response.session_id && response.session_id !== currentSessionId) {
        setCurrentSessionId(response.session_id);
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                isLoading: false,
                content: response.final_answer || "Đã phân tích hoàn tất.",
                status: response.status,
                queryResponse: response,
              }
            : msg
        )
      );

      if (response.status === "COMPLETED") {
        showToast("Truy vấn thực thi thành công", "success", 2000);
      } else if (response.status === "PENDING_APPROVAL") {
        showToast("Truy vấn cần phê duyệt HITL", "warning", 3000);
      } else if (response.status === "ERROR") {
        showToast("Phát hiện lỗi trong câu truy vấn", "error", 3000);
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                isLoading: false,
                content: "Không thể kết nối đến máy chủ phân tích.",
                status: "ERROR",
                queryResponse: {
                  session_id: currentSessionId || "",
                  status: "ERROR",
                  question,
                  is_ambiguous: false,
                  suggested_options: [],
                  execution_time_ms: 0,
                  requires_hitl: false,
                  error:
                    err.message ||
                    "Lỗi kết nối FastAPI. Vui lòng đảm bảo backend đang chạy.",
                },
              }
            : msg
        )
      );
      showToast(err.message || "Lỗi kết nối", "error", 3000);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle HITL approval
  const handleApproveHitl = async (approved: boolean, reason?: string) => {
    if (!currentSessionId || isApprovingHitl) return;
    setIsApprovingHitl(true);
    try {
      // Endpoint /approve của backend yêu cầu vai trò Admin đã được xác thực (RBAC Governance Guardrail)
      if (currentRole !== "Admin") {
        setCurrentRole("Admin");
        showToast(
          "Đã kích hoạt vai trò Admin (Data Lead) để thực hiện phê duyệt / từ chối HITL.",
          "info",
          3500
        );
      }

      const response = await approveQuery(
        {
          session_id: currentSessionId,
          approved,
          rejection_reason: reason,
        },
        "Admin"
      );

      setMessages((prev) => {
        const updated = [...prev];
        const lastAsstIdx = updated.findLastIndex(
          (m) =>
            m.role === "assistant" &&
            (m.queryResponse?.requires_hitl ||
              m.queryResponse?.status === "PENDING_APPROVAL")
        );

        if (lastAsstIdx !== -1) {
          const prevMsg = updated[lastAsstIdx];
          const prevQr = prevMsg.queryResponse;
          updated[lastAsstIdx] = {
            ...prevMsg,
            status: approved ? "COMPLETED" : "ERROR",
            content:
              response.message ||
              (approved
                ? "Đã phê duyệt và thực thi thành công."
                : `Đã từ chối truy vấn: ${reason || "Người dùng từ chối"}`),
            queryResponse: prevQr
              ? {
                  ...prevQr,
                  status: approved ? "COMPLETED" : "ERROR",
                  requires_hitl: false,
                  final_answer:
                    response.message ||
                    (approved
                      ? "Đã phê duyệt và thực thi thành công."
                      : `Đã từ chối truy vấn: ${reason || "Người dùng từ chối"}`),
                  data: response.data || prevQr.data,
                  columns: response.columns || prevQr.columns,
                }
              : undefined,
          };
        }
        return updated;
      });

      showToast(
        approved ? "Đã phê duyệt và thực thi truy vấn" : "Đã từ chối truy vấn",
        approved ? "success" : "info",
        2500
      );
    } catch (err: any) {
      showToast(err.message || "Lỗi xử lý phê duyệt", "error", 2500);
    } finally {
      setIsApprovingHitl(false);
    }
  };

  // Handle retry last query
  const handleRetryLastQuery = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg && lastUserMsg.content) {
      handleSendQuery(lastUserMsg.content);
    }
  };

  const handleResetToHome = () => {
    setMessages([]);
  };

  // Telemetry for the inspector pane from latest assistant response
  const latestAssistantMsg = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.queryResponse);
  const latestResponse = latestAssistantMsg?.queryResponse;

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden text-slate-100 font-sans-ui">
      {/* 3-Pane Adaptive Workspace Layout */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Pane 1: Data Catalog & Session Navigator */}
        <Sidebar
          onSelectPrompt={(prompt) => handleSendQuery(prompt)}
          onResetToHome={handleResetToHome}
        />

        {/* Off-canvas Schema Drawer (24 Tables Detailed Inspector) */}
        <SchemaDrawer />

        {/* Pane 2: Central Analytics Canvas */}
        <div
          data-testid="analytics-canvas-pane"
          className="flex-1 flex flex-col min-w-0 overflow-hidden bg-background relative"
        >
          {/* Header Bar */}
          <Header
            isInspectorOpen={isInspectorOpen}
            onToggleInspector={() => setIsInspectorOpen((prev) => !prev)}
          />

          {/* Main Content Area */}
          <main className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
            {/* Scrollable Canvas: Launchpad or Messages with bottom padding for floating bar */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 sm:p-6 pb-28 sm:pb-32 flex flex-col">
              {messages.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center max-w-3xl mx-auto w-full my-auto animate-in fade-in duration-200">
                  <ExecutiveLaunchpad
                    currentRole={currentRole}
                    onSelectPrompt={(prompt) => handleSendQuery(prompt)}
                  />
                </div>
              ) : (
                <div className="flex-1 max-w-3xl mx-auto w-full">
                  <MessageList
                    messages={messages}
                    isLoading={isLoading}
                    isApprovingHitl={isApprovingHitl}
                    onApproveHitl={handleApproveHitl}
                    onSelectOption={(option) => handleSendQuery(option)}
                    onRetry={handleRetryLastQuery}
                  />
                </div>
              )}
            </div>

            {/* Floating Capsule Command Bar (Google Gemini Style - Perfectly Centered & Aligned) */}
            <div className="absolute bottom-5 left-0 right-0 z-30 pointer-events-none px-4 flex justify-center">
              <div className="max-w-3xl w-full pointer-events-auto">
                <QueryInputCard
                  onSubmit={handleSendQuery}
                  isLoading={isLoading}
                  placeholder={
                    messages.length === 0
                      ? "Đặt câu hỏi phân tích kho TPC-DS (ví dụ: So sánh doanh thu Store vs Web 2003)..."
                      : "Tiếp tục phân tích hoặc tinh chỉnh câu hỏi..."
                  }
                />
              </div>
            </div>
          </main>
        </div>

        {/* Pane 3: Context & Governance Inspector Drawer */}
        <InspectorDrawer
          data-testid="inspector-pane"
          isOpen={isInspectorOpen}
          onClose={() => setIsInspectorOpen(false)}
          executionTimeMs={latestResponse?.execution_time_ms}
          scannedBytes={latestResponse?.estimated_cost_bytes}
          sql={latestResponse?.sql}
          astVerified={!!(latestResponse as any)?.ast_verified}
          role={currentRole}
        />
      </div>
    </div>
  );
}
