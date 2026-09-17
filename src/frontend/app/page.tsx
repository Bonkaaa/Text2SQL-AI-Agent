"use client";

import React from "react";
import {
  Database,
  ShieldCheck,
  Sparkles,
  Layers,
  ArrowRight,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { SchemaDrawer } from "@/components/layout/SchemaDrawer";
import { useAppContext } from "@/context/AppContext";

export default function HomePage() {
  const { currentRole, currentSessionId, isSchemaDrawerOpen, showToast } =
    useAppContext();

  const handleSelectPrompt = (promptText: string) => {
    showToast(`Đã chọn câu hỏi: "${promptText}"`, "info", 3000);
  };

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      {/* 1. Header Top Navigation */}
      <Header />

      {/* 2. Main Workspace (Sidebar + Content Canvas + Schema Drawer) */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Navigation Sidebar */}
        <Sidebar onSelectPrompt={handleSelectPrompt} />

        {/* Right Off-canvas Schema Drawer */}
        <SchemaDrawer />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto custom-scrollbar flex flex-col items-center justify-center p-6 sm:p-12">
          <div className="glass-card p-8 rounded-2xl max-w-2xl w-full text-center space-y-6 shadow-card border border-surface-border animate-in fade-in duration-300">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-sm font-medium">
              <Sparkles className="w-4 h-4 text-brand-400" />
              <span>Conversational BI & Self-Service Analytics</span>
            </div>

            <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              Text2SQL AI Agent
            </h1>

            <p className="text-slate-400 text-sm leading-relaxed max-w-lg mx-auto">
              Hệ thống AI Agent tự phục vụ phân tích dữ liệu kho TPC-H (8 bảng) bằng
              tiếng Việt. Tích hợp DeepAgents Supervisor và LangGraph Control Pipeline.
            </p>

            {/* Quick Context Inspector Box */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-left">
              <div className="p-3.5 rounded-xl bg-surface-subtle/50 border border-surface-border">
                <div className="text-xs text-slate-400 mb-1 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
                  <span>Vai trò hiện tại</span>
                </div>
                <div className="text-sm font-semibold text-slate-100">
                  {currentRole}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-subtle/50 border border-surface-border">
                <div className="text-xs text-slate-400 mb-1 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-success" />
                  <span>Phiên làm việc</span>
                </div>
                <div className="text-xs font-mono font-medium text-slate-200 truncate">
                  {currentSessionId || "Đang khởi tạo..."}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-subtle/50 border border-surface-border">
                <div className="text-xs text-slate-400 mb-1 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-amber-400" />
                  <span>Schema Drawer</span>
                </div>
                <div className="text-sm font-semibold text-slate-100">
                  {isSchemaDrawerOpen ? "Đang mở" : "Đang đóng"}
                </div>
              </div>
            </div>

            {/* Toast test trigger button */}
            <div className="pt-2">
              <button
                onClick={() =>
                  showToast(
                    "Thanh điều hướng Sidebar đã kết nối thành công với AppContext!",
                    "success"
                  )
                }
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-glow transition-all active:scale-95"
              >
                <span>Thử nghiệm Toast Thông Báo</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
