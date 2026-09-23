"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  Check,
  ChevronsUpDown,
  Home,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  ShieldCheck,
  Sparkles,
  SquarePen,
  Trash2,
} from "lucide-react";
import { SessionRecord, useAppContext } from "@/context/AppContext";

export const PROMPT_PRESETS = [
  {
    id: "top_customers",
    prompt: "Top 5 khách hàng có tổng chi tiêu lớn nhất năm 1995",
    timeGroup: "today",
  },
  {
    id: "revenue_by_region",
    prompt: "Phân tích doanh thu thuần theo 5 khu vực địa lý",
    timeGroup: "today",
  },
  {
    id: "late_shipments",
    prompt: "Tỷ lệ đơn hàng giao trễ theo phương thức vận chuyển (AIR, TRUCK, SHIP)",
    timeGroup: "past",
  },
  {
    id: "discount_analysis",
    prompt: "Mức chiết khấu trung bình của các dòng sản phẩm TPC-H",
    timeGroup: "past",
  },
];

interface SidebarProps {
  onSelectPrompt?: (prompt: string) => void;
  onResetToHome?: () => void;
}

export function Sidebar({ onSelectPrompt, onResetToHome }: SidebarProps) {
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
    setCurrentRole,
    showToast,
  } = useAppContext();

  const [searchQuery, setSearchQuery] = useState("");
  const [isRoleDropdownOpen, setRoleDropdownOpen] = useState(false);
  const [isLogoHovered, setIsLogoHovered] = useState(false);

  const isAnalyst = currentRole === "Analyst";
  const isAdmin = currentRole === "Admin";
  const persona = isAnalyst
    ? {
        name: "Nguyễn Văn An",
        initials: "NA",
        roleTitle: "Supply Chain & Sales Analyst",
      }
    : {
        name: "Trần Thị Bình",
        initials: "TB",
        roleTitle: "Data Lead & Governance Admin",
      };

  const handleNewChat = () => {
    startNewSession();
    if (onResetToHome) {
      onResetToHome();
    }
    showToast("Đã tạo phiên hội thoại mới", "info", 1500);
  };

  const handleHomeClick = () => {
    if (onResetToHome) {
      onResetToHome();
    } else {
      startNewSession();
    }
    showToast("Đã chuyển về trang hội thoại chính", "info", 1500);
  };

  const handlePromptClick = (promptText: string) => {
    if (onSelectPrompt) {
      onSelectPrompt(promptText);
    }
  };

  // Filter history by search query
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessionHistory;
    const q = searchQuery.toLowerCase();
    return sessionHistory.filter((s) => s.title.toLowerCase().includes(q));
  }, [sessionHistory, searchQuery]);

  return (
    <>
      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-[#0b0e17] border-r border-white/5 backdrop-blur-xl transition-all duration-300 ease-in-out lg:static lg:z-auto overflow-hidden ${
          isSidebarOpen
            ? "w-64 translate-x-0"
            : "-translate-x-full lg:translate-x-0 lg:w-16"
        }`}
      >
        {/* =============================================================== */}
        {/* TOP BRAND HEADER / LOGO HOVER EXPAND                            */}
        {/* =============================================================== */}
        <div className="flex items-center justify-between p-3.5 border-b border-white/5 h-16 flex-shrink-0">
          {isSidebarOpen ? (
            /* --- EXPANDED MODE: Logo + Brand + Collapse Button --- */
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-500 text-white shadow-glow flex-shrink-0">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold tracking-tight text-white">
                    Text2SQL
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-300 font-semibold border border-brand-500/30">
                    TPC-H
                  </span>
                </div>
              </div>

              <button
                onClick={toggleSidebar}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                title="Thu gọn thanh điều hướng"
              >
                <PanelLeftClose className="w-4 h-4 hidden lg:block" />
              </button>
            </div>
          ) : (
            /* --- COLLAPSED MODE: Logo hover to show expand icon (Image 1 style) --- */
            <div className="w-full flex items-center justify-center">
              <button
                onClick={toggleSidebar}
                onMouseEnter={() => setIsLogoHovered(true)}
                onMouseLeave={() => setIsLogoHovered(false)}
                className="h-10 w-10 rounded-2xl flex items-center justify-center bg-gradient-to-tr from-brand-600 to-indigo-500 text-white shadow-glow transition-all duration-200 hover:scale-105 active:scale-95 cursor-pointer"
                title="Mở rộng thanh điều hướng"
              >
                {isLogoHovered ? (
                  <PanelLeftOpen className="h-5 w-5 animate-in zoom-in-75 duration-150" />
                ) : (
                  <Sparkles className="h-5 w-5" />
                )}
              </button>
            </div>
          )}
        </div>

        {/* =============================================================== */}
        {/* COLLAPSED MODE: ONLY HOME ICON & EMPTY MIDDLE (Image 1 style)    */}
        {/* =============================================================== */}
        {!isSidebarOpen && (
          <div className="flex-1 flex flex-col items-center justify-between py-4">
            {/* Top: Home Icon (clicking returns to new chat screen) */}
            <button
              onClick={handleHomeClick}
              className="h-10 w-10 rounded-2xl flex items-center justify-center bg-brand-500/20 text-brand-300 border border-brand-500/30 hover:bg-brand-500/30 transition-all shadow-sm"
              title="Trang chủ (Cuộc trò chuyện mới)"
            >
              <Home className="w-5 h-5" />
            </button>

            {/* Middle: Empty space as requested (no chat bubbles!) */}
            <div className="flex-1" />

            {/* Bottom: User Avatar (Persona NA / TB) */}
            <div
              onClick={handleHomeClick}
              className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-xs font-bold ring-2 ring-white/10 cursor-pointer shadow-sm hover:scale-105 transition-transform ${
                isAnalyst
                  ? "bg-gradient-to-tr from-brand-500 via-indigo-500 to-purple-500"
                  : "bg-gradient-to-tr from-amber-500 via-orange-500 to-yellow-500"
              }`}
              title={`Tài khoản: ${persona.name} (${currentRole})`}
            >
              {persona.initials}
            </div>
          </div>
        )}

        {/* =============================================================== */}
        {/* EXPANDED MODE CONTENT                                           */}
        {/* =============================================================== */}
        {isSidebarOpen && (
          <>
            {/* 1. "New chat" button matching Image 2 style */}
            <div className="p-3 pb-1">
              <button
                onClick={handleNewChat}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-[#171922] hover:bg-[#1f2230] active:scale-98 text-white text-xs font-semibold border border-white/10 shadow-sm transition-all"
                title="Khởi tạo cuộc trò chuyện mới"
              >
                <SquarePen className="w-4 h-4 text-slate-300 flex-shrink-0" />
                <span>New chat</span>
              </button>
            </div>

            {/* 2. Home Navigation Link */}
            <div className="px-3 pt-1 pb-1">
              <button
                onClick={handleHomeClick}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                title="Về giao diện bắt đầu"
              >
                <Home className="w-4 h-4 text-brand-400 flex-shrink-0" />
                <span>Home</span>
              </button>
            </div>

            {/* 3. Search Box with ⌘K */}
            <div className="px-3 py-1 flex-shrink-0">
              <div className="relative flex items-center">
                <Search className="w-3.5 h-3.5 absolute left-3 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="w-full bg-[#151824] border border-white/5 text-slate-200 text-xs rounded-xl pl-8 pr-8 py-1.5 outline-none focus:border-brand-400/40 transition-colors placeholder:text-slate-500"
                />
                <kbd className="absolute right-2.5 text-[10px] text-slate-400 bg-[#0e111a] px-1.5 py-0.5 rounded border border-white/10 font-mono pointer-events-none">
                  ⌘K
                </kbd>
              </div>
            </div>

            {/* 4. Chat History Feed (Grouped: Hôm nay, 7 ngày trước) */}
            <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-4">
              {/* Group 1: Hôm nay */}
              <div>
                <div className="px-2 mb-1.5 text-[11px] font-medium text-slate-500">
                  Hôm nay
                </div>

                <div className="space-y-0.5">
                  {filteredSessions.slice(0, 3).map((session) => {
                    const isActive = session.id === currentSessionId;
                    return (
                      <div
                        key={session.id}
                        onClick={() => setCurrentSessionId(session.id)}
                        className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-all ${
                          isActive
                            ? "bg-white/10 text-white font-medium"
                            : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                        }`}
                      >
                        <span className="truncate flex-1 pr-2">{session.title}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(session.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-500 hover:text-rose-400 transition-opacity"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}

                  {/* Sample presets */}
                  {PROMPT_PRESETS.filter((p) => p.timeGroup === "today").map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handlePromptClick(item.prompt)}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all truncate block"
                      title={item.prompt}
                    >
                      {item.prompt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Group 2: 7 ngày trước */}
              <div>
                <div className="px-2 mb-1.5 text-[11px] font-medium text-slate-500">
                  7 ngày trước
                </div>

                <div className="space-y-0.5">
                  {filteredSessions.slice(3, 7).map((session) => (
                    <div
                      key={session.id}
                      onClick={() => setCurrentSessionId(session.id)}
                      className="group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-white/5 cursor-pointer transition-all"
                    >
                      <span className="truncate flex-1 pr-2">{session.title}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession(session.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-500 hover:text-rose-400 transition-opacity"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}

                  {PROMPT_PRESETS.filter((p) => p.timeGroup === "past").map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handlePromptClick(item.prompt)}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all truncate block"
                      title={item.prompt}
                    >
                      {item.prompt}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* 5. Bottom User Profile Card (Persona & Role Switcher) */}
            <div className="p-2 border-t border-white/5 bg-[#090c14] flex-shrink-0 relative">
              <div
                onClick={() => setRoleDropdownOpen(!isRoleDropdownOpen)}
                className="flex items-center justify-between p-2 rounded-xl hover:bg-white/5 cursor-pointer transition-colors"
                title="Bấm để đổi vai trò (Analyst / Admin)"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ring-2 ring-white/10 flex-shrink-0 ${
                      isAnalyst
                        ? "bg-gradient-to-tr from-brand-500 via-indigo-500 to-purple-500"
                        : "bg-gradient-to-tr from-amber-500 via-orange-500 to-yellow-500"
                    }`}
                  >
                    {persona.initials}
                  </div>
                  <div className="truncate flex-1 min-w-0">
                    <div className="text-xs font-semibold text-slate-100 truncate">
                      {persona.name}
                    </div>
                    <div className="text-[10px] text-slate-400 truncate flex items-center gap-1">
                      <span>{currentRole}</span>
                      <span>•</span>
                      <span>{isAnalyst ? "Supply Chain" : "Governance"}</span>
                    </div>
                  </div>
                </div>

                <ChevronsUpDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
              </div>

              {/* Role Dropdown */}
              {isRoleDropdownOpen && (
                <div className="absolute bottom-full left-2 right-2 mb-1 p-1 rounded-xl bg-[#171a25] border border-white/10 shadow-card z-50 animate-in fade-in slide-in-from-bottom-2 duration-150">
                  <div className="text-[10px] uppercase tracking-wider text-slate-400 px-2 py-1 font-semibold">
                    Đổi vai trò
                  </div>
                  <button
                    onClick={() => {
                      setCurrentRole("Analyst");
                      setRoleDropdownOpen(false);
                      showToast("Đã chuyển sang vai trò: Analyst (Nguyễn Văn An)", "info", 1500);
                    }}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                      currentRole === "Analyst"
                        ? "bg-brand-500/20 text-brand-300 font-semibold"
                        : "text-slate-300 hover:bg-white/5"
                    }`}
                  >
                    <span>Analyst (Nguyễn Văn An)</span>
                    {currentRole === "Analyst" && <Check className="w-3.5 h-3.5" />}
                  </button>

                  <button
                    onClick={() => {
                      setCurrentRole("Admin");
                      setRoleDropdownOpen(false);
                      showToast("Đã chuyển sang vai trò: Admin (Trần Thị Bình)", "info", 1500);
                    }}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                      currentRole === "Admin"
                        ? "bg-amber-500/20 text-amber-300 font-semibold"
                        : "text-slate-300 hover:bg-white/5"
                    }`}
                  >
                    <span>Admin (Trần Thị Bình)</span>
                    {currentRole === "Admin" && <Check className="w-3.5 h-3.5" />}
                  </button>

                  {isAdmin && (
                    <div className="border-t border-white/10 mt-1 pt-1">
                      <Link
                        href="/audit"
                        className="w-full flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-amber-300 hover:bg-amber-500/15 transition-colors font-medium"
                      >
                        <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                        <span>Nhật ký Audit</span>
                      </Link>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </aside>
    </>
  );
}
