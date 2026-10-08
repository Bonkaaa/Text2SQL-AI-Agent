"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  Check,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Database,
  Home,
  Layers,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  SquarePen,
  Trash2,
  Undo2,
  Users,
  Warehouse,
  Info,
} from "lucide-react";
import { SessionRecord, useAppContext } from "@/context/AppContext";
import { TPCDS_DOMAINS, TOTAL_TPCDS_TABLES_COUNT } from "@/data/tpcdsCatalog";
import { TableMetadataModal } from "../modal/TableMetadataModal";

export const PROMPT_PRESETS = [
  {
    id: "omnichannel_sales",
    prompt: "So sánh tổng doanh thu thuần (Net Paid) giữa 3 kênh store, web và catalog năm 2003",
    timeGroup: "today",
  },
  {
    id: "return_rate",
    prompt: "Top 10 mặt hàng có tỷ lệ hoàn hàng cao nhất trong quý 3",
    timeGroup: "today",
  },
  {
    id: "inventory_alerts",
    prompt: "Cảnh báo tồn kho dưới 500 đơn vị tại các kho miền Tây",
    timeGroup: "past",
  },
  {
    id: "promotion_margin",
    prompt: "Tác động của chiến dịch khuyến mãi đến lợi nhuận biên",
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
  const [isCatalogOpen, setIsCatalogOpen] = useState(true);
  const [expandedDomain, setExpandedDomain] = useState<string | null>("sales");
  const [inspectingTable, setInspectingTable] = useState<string | null>(null);

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
    showToast("Đã tạo phiên phân tích mới", "info", 1500);
  };

  const handleHomeClick = () => {
    if (onResetToHome) {
      onResetToHome();
    } else {
      startNewSession();
    }
    showToast("Đã chuyển về màn hình làm việc chính", "info", 1500);
  };

  const handlePromptClick = (promptText: string) => {
    if (onSelectPrompt) {
      onSelectPrompt(promptText);
    }
  };

  const handleTableClick = (tableName: string) => {
    if (onSelectPrompt) {
      onSelectPrompt(`Phân tích tổng quan và cấu trúc dữ liệu của bảng ${tableName}`);
    } else {
      showToast(`Đã chọn bảng ${tableName}`, "info", 1500);
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
        data-testid="sidebar-pane"
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-surface border-r border-surface-border transition-all duration-200 ease-in-out lg:static lg:z-auto overflow-hidden ${
          isSidebarOpen
            ? "w-64 translate-x-0"
            : "-translate-x-full lg:translate-x-0 lg:w-16"
        }`}
      >
        {/* =============================================================== */}
        {/* TOP BRAND HEADER / LOGO HOVER EXPAND                            */}
        {/* =============================================================== */}
        <div className="flex items-center justify-between p-3.5 border-b border-slate-200 dark:border-surface-border h-14 flex-shrink-0 bg-slate-50 dark:bg-surface-secondary/40">
          {isSidebarOpen ? (
            /* --- EXPANDED MODE: Logo + Brand + Collapse Button --- */
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm flex-shrink-0">
                  <Database className="h-4 w-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold tracking-tight text-slate-900 dark:text-white font-sans-ui">
                    Text2SQL
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 font-semibold border border-blue-200 dark:border-blue-500/30">
                    TPC-DS
                  </span>
                </div>
              </div>

              <button
                onClick={toggleSidebar}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-surface-tertiary transition-colors"
                title="Thu gọn thanh điều hướng"
              >
                <PanelLeftClose className="w-4 h-4 hidden lg:block" />
              </button>
            </div>
          ) : (
            /* --- COLLAPSED MODE: Logo hover to show expand icon --- */
            <div className="w-full flex items-center justify-center">
              <button
                onClick={toggleSidebar}
                onMouseEnter={() => setIsLogoHovered(true)}
                onMouseLeave={() => setIsLogoHovered(false)}
                className="h-9 w-9 rounded-xl flex items-center justify-center bg-brand-600 text-white shadow-sm transition-all duration-150 hover:scale-105 active:scale-95 cursor-pointer"
                title="Mở rộng thanh điều hướng"
              >
                {isLogoHovered ? (
                  <PanelLeftOpen className="h-4 w-4" />
                ) : (
                  <Database className="h-4 w-4" />
                )}
              </button>
            </div>
          )}
        </div>

        {/* =============================================================== */}
        {/* COLLAPSED MODE: ONLY HOME ICON & EMPTY MIDDLE                   */}
        {/* =============================================================== */}
        {!isSidebarOpen && (
          <div className="flex-1 flex flex-col items-center justify-between py-4">
            <button
              onClick={handleHomeClick}
              className="h-9 w-9 rounded-xl flex items-center justify-center bg-slate-100 dark:bg-surface-secondary text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-surface-border hover:bg-slate-200 dark:hover:bg-surface-tertiary transition-all"
              title="Trang chủ (Khởi động phân tích)"
            >
              <Home className="w-4 h-4" />
            </button>

            <div className="flex-1" />

            <div
              onClick={handleHomeClick}
              className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold ring-1 ring-white/10 cursor-pointer hover:scale-105 transition-transform ${
                isAnalyst ? "bg-blue-600" : "bg-amber-600"
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
            {/* 1. New Chat Button */}
            <div className="p-3 pb-1">
              <button
                onClick={handleNewChat}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-surface-secondary dark:hover:bg-surface-tertiary text-slate-800 dark:text-white text-xs font-semibold border border-slate-200 dark:border-surface-border shadow-xs transition-all"
                title="Khởi tạo phân tích mới"
              >
                <SquarePen className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                <span>Phân tích mới</span>
              </button>
            </div>

            {/* 2. Home Navigation Link */}
            <div className="px-3 py-1">
              <button
                onClick={handleHomeClick}
                className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-surface-tertiary transition-all"
              >
                <Home className="w-3.5 h-3.5 text-slate-400" />
                <span>Trang làm việc</span>
              </button>
            </div>

            {/* 3. Search Box */}
            <div className="px-3 py-1 flex-shrink-0">
              <div className="relative flex items-center">
                <Search className="w-3.5 h-3.5 absolute left-3 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Tìm kiếm session/bảng..."
                  className="w-full bg-slate-100 dark:bg-surface-secondary/70 border border-slate-200 dark:border-surface-border text-slate-800 dark:text-slate-200 text-xs rounded-lg pl-8 pr-3 py-1.5 outline-none focus:border-brand-500/50 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-500"
                />
              </div>
            </div>

            {/* 4. Scrollable Middle: Session History (100% Focus) */}
            <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-2">
              <div className="flex items-center justify-between px-2 pt-1 pb-1 text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                <span>Lịch sử phân tích</span>
                <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                  {filteredSessions.length} phiên
                </span>
              </div>

              {filteredSessions.length === 0 ? (
                <div className="px-2 py-6 text-center text-xs text-slate-400 italic">
                  Chưa có phiên phân tích nào.
                </div>
              ) : (
                <div className="space-y-1">
                  {filteredSessions.map((session) => {
                    const isActive = session.id === currentSessionId;
                    return (
                      <div
                        key={session.id}
                        onClick={() => setCurrentSessionId(session.id)}
                        className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                          isActive
                            ? "bg-blue-50 dark:bg-brand-600/20 text-blue-700 dark:text-blue-300 font-medium border border-blue-200 dark:border-brand-500/30 shadow-xs"
                            : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-surface-secondary/60"
                        }`}
                      >
                        <span className="truncate flex-1 pr-2">{session.title}</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(session.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 rounded transition-all"
                          title="Xóa phiên phân tích"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* 5. User Profile Card */}
            <div className="p-2 border-t border-slate-200 dark:border-surface-border bg-slate-50 dark:bg-surface-secondary/40 flex-shrink-0">
              <div
                onClick={() => setRoleDropdownOpen(!isRoleDropdownOpen)}
                className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-surface-tertiary cursor-pointer transition-colors"
                title="Bấm để đổi vai trò (Analyst / Admin)"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-[11px] font-bold ${
                      isAnalyst ? "bg-blue-600" : "bg-amber-600"
                    }`}
                  >
                    {persona.initials}
                  </div>
                  <div className="truncate">
                    <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                      {persona.name}
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
                      {currentRole}
                    </div>
                  </div>
                </div>
                <ChevronsUpDown className="w-3.5 h-3.5 text-slate-400" />
              </div>
            </div>
          </>
        )}
      </aside>

      {/* Table Metadata Detail Modal */}
      <TableMetadataModal
        isOpen={!!inspectingTable}
        tableName={inspectingTable}
        onClose={() => setInspectingTable(null)}
        onSelectForPrompt={(tableName) => {
          if (onSelectPrompt) {
            onSelectPrompt(`Phân tích các chỉ số chính từ bảng ${tableName}`);
          }
        }}
      />
    </>
  );
}
