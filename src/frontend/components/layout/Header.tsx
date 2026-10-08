"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  Database,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Sun,
  Moon,
  TableProperties,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";
import { RoleSwitcher } from "@/components/layout/RoleSwitcher";

export interface HeaderProps {
  isInspectorOpen?: boolean;
  onToggleInspector?: () => void;
}

export function Header({
  isInspectorOpen = false,
  onToggleInspector,
}: HeaderProps) {
  const {
    health,
    refreshHealth,
    isSchemaDrawerOpen,
    toggleSchemaDrawer,
    showToast,
    theme,
    toggleTheme,
  } = useAppContext();

  const [isEngineMenuOpen, setEngineMenuOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await refreshHealth();
    setIsRefreshing(false);
    showToast("Đã cập nhật trạng thái kết nối Warehouse.", "info", 1800);
  };

  return (
    <header className="sticky top-0 z-30 w-full border-b border-slate-200 dark:border-surface-border bg-white/90 dark:bg-surface/90 backdrop-blur-md transition-colors flex-shrink-0">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        {/* ================================================================= */}
        {/* LEFT: ENGINE / MODEL SELECTOR PILL                                */}
        {/* ================================================================= */}
        <div className="flex items-center gap-3">
          {/* Model Selector Dropdown Pill */}
          <div className="relative">
            <button
              onClick={() => setEngineMenuOpen(!isEngineMenuOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-surface-secondary dark:hover:bg-surface-tertiary border border-slate-200 dark:border-surface-border text-xs font-semibold text-slate-800 dark:text-slate-200 transition-all shadow-xs active:scale-98"
            >
              <div className="w-4 h-4 rounded-md bg-blue-600 flex items-center justify-center text-white flex-shrink-0">
                <Database className="w-2.5 h-2.5" />
              </div>
              <span className="font-sans-ui">DeepAgents TPC-DS</span>
              <span className="relative flex h-1.5 w-1.5 ml-0.5">
                <span
                  className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    health.isConnected ? "bg-emerald-400" : "bg-amber-400"
                  }`}
                />
                <span
                  className={`relative inline-flex rounded-full h-1.5 w-1.5 ${
                    health.isConnected ? "bg-emerald-400" : "bg-amber-400"
                  }`}
                />
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-0.5" />
            </button>

            {/* Engine Info Dropdown */}
            {isEngineMenuOpen && (
              <div className="absolute top-full left-0 mt-1.5 w-64 p-3 rounded-2xl bg-white dark:bg-[#0d1527] border border-slate-200 dark:border-slate-700/80 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-150 space-y-2.5">
                <div className="text-[11px] font-bold text-slate-500 dark:text-slate-300 uppercase tracking-wider">
                  Cấu hình AI Agent
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-surface-secondary border border-slate-100 dark:border-transparent">
                    <span className="text-slate-500 dark:text-slate-400">Warehouse:</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">DuckDB TPC-DS (24 bảng)</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-surface-secondary border border-slate-100 dark:border-transparent">
                    <span className="text-slate-500 dark:text-slate-400">Trạng thái:</span>
                    <span
                      className={`font-semibold ${
                        health.isConnected
                          ? "text-emerald-600 dark:text-emerald-400"
                          : health.status === "disconnected"
                          ? "text-rose-600 dark:text-rose-400"
                          : "text-amber-600 dark:text-amber-400"
                      }`}
                    >
                      {health.isConnected
                        ? "Sẵn sàng (200 OK)"
                        : health.status === "disconnected"
                        ? "Mất kết nối"
                        : "Đang kiểm tra"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-surface-secondary border border-slate-100 dark:border-transparent">
                    <span className="text-slate-500 dark:text-slate-400">Độ trễ:</span>
                    <span className="font-mono text-slate-800 dark:text-slate-200">
                      {health.latencyMs}ms
                    </span>
                  </div>
                </div>

                <button
                  onClick={handleManualRefresh}
                  disabled={isRefreshing}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors"
                >
                  <RefreshCw
                    className={`w-3 h-3 ${isRefreshing ? "animate-spin" : ""}`}
                  />
                  <span>Kiểm tra lại kết nối</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ================================================================= */}
        {/* RIGHT: THEME TOGGLE, ROLE SWITCHER & INSPECTOR TOGGLE             */}
        {/* ================================================================= */}
        <div className="flex items-center gap-2">
          {/* Theme Toggle Button (Light / Dark) */}
          <button
            type="button"
            onClick={toggleTheme}
            className="flex items-center justify-center w-8 h-8 rounded-xl bg-slate-100 dark:bg-surface-secondary text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-surface-border hover:bg-slate-200 dark:hover:bg-surface-tertiary hover:text-slate-900 dark:hover:text-white transition-all shadow-xs"
            title={theme === "dark" ? "Chuyển sang giao diện Sáng" : "Chuyển sang giao diện Tối"}
            aria-label="Đổi theme sáng/tối"
          >
            {theme === "dark" ? (
              <Sun className="w-3.5 h-3.5 text-amber-500" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-indigo-600" />
            )}
          </button>

          {/* Role Switcher (Analyst / Admin) */}
          <RoleSwitcher />

          {/* Schema Drawer Toggle Button */}
          <button
            onClick={toggleSchemaDrawer}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isSchemaDrawerOpen
                ? "bg-blue-100 dark:bg-brand-500/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-brand-500/40"
                : "bg-slate-100 dark:bg-surface-secondary text-slate-700 dark:text-slate-300 border-slate-200 dark:border-surface-border hover:bg-slate-200 dark:hover:bg-surface-tertiary hover:text-slate-900 dark:hover:text-white"
            }`}
            title="Tra cứu 24 bảng TPC-DS"
          >
            <TableProperties className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span className="hidden sm:inline">Schema</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-surface-tertiary text-slate-700 dark:text-slate-300 font-mono">
              24
            </span>
          </button>

          {/* Inspector Drawer Toggle Button */}
          {onToggleInspector && (
            <button
              onClick={onToggleInspector}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                isInspectorOpen
                  ? "bg-blue-100 dark:bg-brand-500/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-brand-500/40"
                  : "bg-slate-100 dark:bg-surface-secondary text-slate-700 dark:text-slate-300 border-slate-200 dark:border-surface-border hover:bg-slate-200 dark:hover:bg-surface-tertiary hover:text-slate-900 dark:hover:text-white"
              }`}
              title="Đóng/mở Context & Governance Inspector (Ctrl+B)"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="hidden sm:inline">Inspector</span>
              <kbd className="hidden lg:inline text-[9px] bg-slate-200 dark:bg-surface-tertiary px-1 py-0.5 rounded text-slate-600 dark:text-slate-400 font-mono">
                ⌘B
              </kbd>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
