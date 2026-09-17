"use client";

import React from "react";
import Link from "next/link";
import {
  Clock,
  Lock,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { SessionRecord, useAppContext } from "@/context/AppContext";

export const PROMPT_PRESETS = [
  {
    id: "top_customers",
    icon: "🏢",
    title: "Top 5 khách hàng",
    prompt: "Top 5 khách hàng có tổng chi tiêu lớn nhất năm 1995",
  },
  {
    id: "revenue_by_region",
    icon: "🌍",
    title: "Doanh số 5 khu vực",
    prompt: "Phân tích doanh thu thuần theo 5 khu vực địa lý",
  },
  {
    id: "late_shipments",
    icon: "🚚",
    title: "Tỷ lệ đơn giao trễ",
    prompt: "Tỷ lệ đơn hàng giao trễ theo phương thức vận chuyển (AIR, TRUCK, SHIP)",
  },
  {
    id: "discount_analysis",
    icon: "📦",
    title: "Chiết khấu sản phẩm",
    prompt: "Mức chiết khấu trung bình của các dòng sản phẩm TPC-H",
  },
];

interface SidebarProps {
  onSelectPrompt?: (prompt: string) => void;
}

export function Sidebar({ onSelectPrompt }: SidebarProps) {
  const {
    currentSessionId,
    setCurrentSessionId,
    startNewSession,
    sessionHistory,
    deleteSession,
    isSidebarOpen,
    setSidebarOpen,
    toggleSidebar,
    currentRole,
    showToast,
  } = useAppContext();

  const isAdmin = currentRole === "ADMIN" || currentRole === "Admin";

  const handleNewSession = () => {
    const newId = startNewSession();
    showToast(`Đã tạo phiên làm việc mới: ${newId.substring(0, 12)}...`, "info");
  };

  const handlePromptClick = (promptText: string) => {
    if (onSelectPrompt) {
      onSelectPrompt(promptText);
    } else {
      showToast(`Đã chọn câu hỏi mẫu: "${promptText}"`, "info");
    }
  };

  const formatRelativeTime = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMinutes = Math.floor(
        (now.getTime() - date.getTime()) / (1000 * 60)
      );

      if (diffMinutes < 1) return "Vừa xong";
      if (diffMinutes < 60) return `${diffMinutes}m trước`;
      const diffHours = Math.floor(diffMinutes / 60);
      if (diffHours < 24) return `${diffHours}h trước`;
      return date.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
      });
    } catch {
      return "Gần đây";
    }
  };

  return (
    <>
      {/* ================================================================= */}
      {/* 1. MOBILE BACKDROP OVERLAY */}
      {/* ================================================================= */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ================================================================= */}
      {/* 2. SIDEBAR CONTAINER: EXPANDED (w-72) HOẶC COLLAPSED MINI (w-16) */}
      {/* ================================================================= */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-surface/95 border-r border-surface-border backdrop-blur-xl transition-all duration-300 ease-in-out lg:static lg:z-auto overflow-hidden ${
          isSidebarOpen
            ? "w-72 translate-x-0"
            : "-translate-x-full lg:translate-x-0 lg:w-16"
        }`}
      >
        {/* ================================================================= */}
        {/* TOP BAR: ACTION NEW SESSION */}
        {/* ================================================================= */}
        <div className="flex items-center justify-between p-3 border-b border-surface-border h-16 flex-shrink-0">
          {isSidebarOpen ? (
            <>
              <button
                onClick={handleNewSession}
                className="flex-1 flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 active:scale-95 text-white text-xs font-semibold shadow-glow transition-all truncate"
                title="Khởi tạo phiên phân tích mới"
              >
                <Plus className="w-4 h-4 flex-shrink-0" />
                <span className="truncate">Phiên hội thoại mới</span>
              </button>

              <button
                onClick={toggleSidebar}
                className="ml-2 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-subtle transition-colors flex-shrink-0"
                title="Thu gọn Sidebar"
              >
                <PanelLeftClose className="w-4 h-4 hidden lg:block" />
                <X className="w-4 h-4 lg:hidden" />
              </button>
            </>
          ) : (
            /* MINI COLLAPSED MODE: Nút dấu + tròn gọn gàng */
            <div className="w-full flex items-center justify-center">
              <button
                onClick={handleNewSession}
                className="w-10 h-10 flex items-center justify-center rounded-xl bg-brand-600 hover:bg-brand-500 active:scale-95 text-white shadow-glow transition-all"
                title="Tạo phiên hội thoại mới (+)"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* MIDDLE: SESSIONS & PRESETS */}
        {/* ================================================================= */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-4">
          {isSidebarOpen ? (
            /* --- EXPANDED MODE --- */
            <>
              {/* Lịch sử các phiên */}
              <div>
                <div className="flex items-center justify-between px-2 mb-2">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-brand-400" />
                    <span>Lịch sử phiên</span>
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-subtle text-slate-400 font-mono">
                    {sessionHistory.length}
                  </span>
                </div>

                {sessionHistory.length === 0 ? (
                  <div className="p-4 text-center text-xs text-slate-500 rounded-xl border border-dashed border-surface-border">
                    Chưa có lịch sử truy vấn
                  </div>
                ) : (
                  <div className="space-y-1">
                    {sessionHistory.map((session: SessionRecord) => {
                      const isActive = session.id === currentSessionId;
                      return (
                        <div
                          key={session.id}
                          onClick={() => setCurrentSessionId(session.id)}
                          className={`group flex items-center justify-between p-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all border ${
                            isActive
                              ? "bg-brand-500/15 text-white border-brand-500/40 shadow-sm"
                              : "text-slate-400 border-transparent hover:bg-surface-subtle/80 hover:text-slate-200"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0 flex-1">
                            <MessageSquare
                              className={`w-3.5 h-3.5 flex-shrink-0 ${
                                isActive ? "text-brand-400" : "text-slate-500"
                              }`}
                            />
                            <div className="truncate flex-1">
                              <div className="truncate">{session.title}</div>
                              <div className="text-[10px] text-slate-500 mt-0.5 font-normal">
                                {formatRelativeTime(session.createdAt)}
                              </div>
                            </div>
                          </div>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteSession(session.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-danger hover:bg-danger/10 rounded-lg transition-all"
                            title="Xóa phiên này"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Gợi ý câu hỏi mẫu */}
              <div>
                <div className="px-2 mb-2 flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  <span>Gợi ý câu hỏi mẫu</span>
                </div>

                <div className="space-y-1.5">
                  {PROMPT_PRESETS.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handlePromptClick(item.prompt)}
                      className="w-full text-left p-2.5 rounded-xl bg-surface-subtle/40 hover:bg-surface-subtle/80 border border-surface-border text-slate-300 hover:text-white transition-all text-xs flex items-start gap-2 active:scale-98"
                    >
                      <span className="text-sm flex-shrink-0 mt-0.5">{item.icon}</span>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-slate-200">{item.title}</div>
                        <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                          {item.prompt}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            /* --- MINI COLLAPSED MODE: Danh sách icon phiên gọn gàng --- */
            <div className="space-y-2 flex flex-col items-center">
              {sessionHistory.slice(0, 8).map((session) => {
                const isActive = session.id === currentSessionId;
                return (
                  <button
                    key={session.id}
                    onClick={() => setCurrentSessionId(session.id)}
                    className={`w-10 h-10 flex items-center justify-center rounded-xl transition-all border ${
                      isActive
                        ? "bg-brand-500/20 text-brand-300 border-brand-500/40 shadow-glow"
                        : "text-slate-400 border-transparent hover:bg-surface-subtle hover:text-white"
                    }`}
                    title={`${session.title} (${formatRelativeTime(session.createdAt)})`}
                  >
                    <MessageSquare className="w-4 h-4" />
                  </button>
                );
              })}

              <div className="w-6 border-t border-surface-border my-2" />

              {/* Icon câu hỏi mẫu mini */}
              {PROMPT_PRESETS.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handlePromptClick(item.prompt)}
                  className="w-10 h-10 flex items-center justify-center rounded-xl hover:bg-surface-subtle text-base transition-all"
                  title={`${item.title}: ${item.prompt}`}
                >
                  {item.icon}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* BOTTOM FOOTER: ADMIN AUDIT LINK */}
        {/* ================================================================= */}
        <div className="p-2.5 border-t border-surface-border bg-surface-subtle/20 flex-shrink-0">
          {isSidebarOpen ? (
            /* --- EXPANDED MODE: Full banner --- */
            isAdmin ? (
              <Link
                href="/audit"
                className="flex items-center justify-between p-2.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-all text-xs font-semibold shadow-sm truncate"
                title="Đi đến bảng điều khiển kiểm toán (Chỉ dành cho Admin)"
              >
                <div className="flex items-center gap-2 truncate">
                  <ShieldCheck className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <span className="truncate">Nhật ký Audit & Quản trị</span>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200 font-mono flex-shrink-0 ml-1">
                  ADMIN
                </span>
              </Link>
            ) : (
              <div
                className="flex items-center justify-between p-2.5 rounded-xl bg-surface-subtle/30 text-slate-500 border border-surface-border text-xs font-medium cursor-not-allowed truncate"
                title="Chức năng yêu cầu quyền Admin (Đổi vai trò tại Header)"
              >
                <div className="flex items-center gap-2 truncate">
                  <Lock className="w-4 h-4 text-slate-500 flex-shrink-0" />
                  <span className="truncate">Nhật ký Audit</span>
                </div>
                <span className="text-[10px] text-slate-500 font-normal flex-shrink-0 ml-1">
                  (Khóa)
                </span>
              </div>
            )
          ) : (
            /* --- MINI COLLAPSED MODE: Icon vuông duy nhất không tràn chữ --- */
            <div className="w-full flex items-center justify-center">
              {isAdmin ? (
                <Link
                  href="/audit"
                  className="w-10 h-10 flex items-center justify-center rounded-xl bg-amber-500/10 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 transition-all shadow-sm"
                  title="Nhật ký Audit & Quản trị (Admin)"
                >
                  <ShieldCheck className="w-5 h-5 text-amber-400" />
                </Link>
              ) : (
                <div
                  className="w-10 h-10 flex items-center justify-center rounded-xl bg-surface-subtle/30 text-slate-600 border border-surface-border cursor-not-allowed"
                  title="Nhật ký Audit (Bị khóa đối với vai trò Analyst)"
                >
                  <Lock className="w-4 h-4 text-slate-500" />
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
