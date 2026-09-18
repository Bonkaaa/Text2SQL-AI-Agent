"use client";

import React, { useState, useEffect, useRef } from "react";
import { Sparkles, TrendingUp, Compass } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { SchemaDrawer } from "@/components/layout/SchemaDrawer";
import { IridescentOrb } from "@/components/chat/IridescentOrb";
import { QueryInputCard } from "@/components/chat/QueryInputCard";
import { ChatMessageItem } from "@/components/chat/ChatMessageItem";
import { useAppContext } from "@/context/AppContext";
import { askQuery, approveQuery } from "@/services/api";
import { ChatMessage, QueryResponse } from "@/types/api";

const QUICK_SUGGESTIONS = [
  {
    label: "Top 5 khách hàng",
    query: "Top 5 khách hàng có tổng chi tiêu lớn nhất năm 1995",
  },
  {
    label: "Doanh số 5 khu vực",
    query: "Phân tích doanh thu thuần theo 5 khu vực địa lý",
  },
  {
    label: "Đơn giao trễ",
    query: "Tỷ lệ đơn hàng giao trễ theo phương thức vận chuyển (AIR, TRUCK, SHIP)",
  },
  {
    label: "Chiết khấu trung bình",
    query: "Mức chiết khấu trung bình của các dòng sản phẩm TPC-H",
  },
];

export default function HomePage() {
  const { currentRole, currentSessionId, showToast } = useAppContext();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > 0) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

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
      const response: QueryResponse = await askQuery({
        question,
        session_id: currentSessionId || undefined,
        role: currentRole,
      });

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
  const handleApproveHitl = async (approved: boolean) => {
    if (!currentSessionId) return;
    try {
      const res = await approveQuery({
        session_id: currentSessionId,
        approved,
      });
      showToast(
        approved ? "Đã phê duyệt truy vấn" : "Đã từ chối truy vấn",
        "info",
        2000
      );
    } catch (err: any) {
      showToast(err.message || "Lỗi xử lý phê duyệt", "error", 2500);
    }
  };

  // Dynamic greeting based on user's current time
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning, Judha";
    if (hour < 18) return "Good Afternoon, Judha";
    return "Good Evening, Judha";
  };

  const handleResetToHome = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-screen bg-[#070b14] overflow-hidden text-slate-100">
      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Navigation Sidebar */}
        <Sidebar
          onSelectPrompt={(prompt) => handleSendQuery(prompt)}
          onResetToHome={handleResetToHome}
        />

        {/* Right Off-canvas Schema Drawer */}
        <SchemaDrawer />

        {/* Center Workspace Canvas */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#090d19]">
          {/* Sub-Header: Engine Dropdown + New Chat + User Avatar */}
          <Header />

          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto custom-scrollbar flex flex-col justify-between">
            {messages.length === 0 ? (
              /* ========================================================= */
              /* HERO / EMPTY STATE: 3D Orb + Greeting + Command Input Box */
              /* ========================================================= */
              <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-4xl mx-auto w-full my-auto animate-in fade-in zoom-in-95 duration-300">
                {/* 3D Iridescent Orb */}
                <IridescentOrb />

                {/* Hero Greeting & Headline (matching sample image) */}
                <div className="space-y-1.5 mt-2 mb-8">
                  <div className="text-sm font-medium text-slate-400 tracking-wide">
                    {getGreeting()}
                  </div>
                  <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white">
                    How Can I{" "}
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-brand-400 via-indigo-300 to-purple-400">
                      Assist You Today?
                    </span>
                  </h1>
                </div>

                {/* Central High-End Command Input Card */}
                <QueryInputCard
                  onSubmit={handleSendQuery}
                  isLoading={isLoading}
                />

                {/* Quick Suggestion Chips */}
                <div className="flex items-center justify-center flex-wrap gap-2 mt-6 max-w-2xl px-4">
                  {QUICK_SUGGESTIONS.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendQuery(item.query)}
                      className="px-3 py-1.5 rounded-full text-xs font-medium text-slate-400 bg-surface-subtle/40 hover:bg-surface-subtle/90 hover:text-slate-200 border border-surface-border transition-all active:scale-95"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* ========================================================= */
              /* ACTIVE CONVERSATION STATE: Chat Thread + Bottom Docked Bar*/
              /* ========================================================= */
              <div className="flex-1 flex flex-col justify-between p-4 sm:p-8 max-w-4xl mx-auto w-full">
                <div className="space-y-2 pb-6">
                  {messages.map((msg) => (
                    <ChatMessageItem
                      key={msg.id}
                      message={msg}
                      onApproveHitl={handleApproveHitl}
                    />
                  ))}
                  <div ref={chatEndRef} />
                </div>

                {/* Bottom Docked Input Box */}
                <div className="sticky bottom-0 pt-4 pb-2 bg-gradient-to-t from-[#090d19] via-[#090d19]/90 to-transparent">
                  <QueryInputCard
                    onSubmit={handleSendQuery}
                    isLoading={isLoading}
                  />
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
