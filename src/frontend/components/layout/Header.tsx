"use client";

import React, { useState } from "react";
import {
  Activity,
  Database,
  Menu,
  PanelLeft,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TableProperties,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";

import { RoleSwitcher } from "@/components/layout/RoleSwitcher";

export function Header() {
  const {
    health,
    refreshHealth,
    isSchemaDrawerOpen,
    toggleSchemaDrawer,
    toggleSidebar,
    isSidebarOpen,
    showToast,
  } = useAppContext();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await refreshHealth();
    setIsRefreshing(false);
    showToast("Đã cập nhật trạng thái kết nối Warehouse.", "info", 2000);
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-surface-border bg-surface/80 backdrop-blur-md transition-colors">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        {/* ================================================================= */}
        {/* 1. BRAND LOGO & SYSTEM TITLE */}
        {/* ================================================================= */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-surface-subtle transition-colors"
            title={isSidebarOpen ? "Thu gọn Sidebar" : "Mở Sidebar"}
          >
            <PanelLeft className="w-5 h-5" />
          </button>

          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 text-white shadow-glow flex-shrink-0">
            <Sparkles className="h-5 w-5" />
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold tracking-tight text-white sm:text-lg">
                Text2SQL<span className="text-brand-400">.AI</span>
              </span>
              <span className="hidden rounded-full bg-brand-500/10 px-2 py-0.5 text-[10px] font-semibold text-brand-300 border border-brand-500/20 sm:inline-block">
                TPC-H Edition
              </span>
            </div>
            <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">
              Self-Service Analytics & Data Governance
            </span>
          </div>
        </div>

        {/* ================================================================= */}
        {/* 2. WAREHOUSE CONNECTION & HEALTH STATUS PILL */}
        {/* ================================================================= */}
        <div className="hidden md:flex items-center gap-2">
          {health.isConnected ? (
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-subtle/70 border border-surface-border text-xs text-slate-300"
              title={`DuckDB Native v${health.version} - Latency: ${health.latencyMs}ms`}
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
              </span>
              <span className="font-semibold text-slate-200">DuckDB TPC-H</span>
              <span className="text-slate-500">•</span>
              <span className="text-success font-mono text-[11px] font-medium">
                {health.latencyMs}ms
              </span>
              <button
                onClick={handleManualRefresh}
                className="ml-1 text-slate-400 hover:text-white transition-colors"
                title="Kiểm tra lại kết nối"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-brand-400" : ""}`}
                />
              </button>
            </div>
          ) : health.status === "checking" ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-subtle/50 border border-surface-border text-xs text-warning">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-warning"></span>
              </span>
              <span>Đang kết nối backend...</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-danger/10 border border-danger/20 text-xs text-danger">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>Chưa kết nối FastAPI</span>
              <button
                onClick={handleManualRefresh}
                className="ml-1 flex items-center gap-1 font-semibold text-danger hover:underline"
              >
                <RefreshCw
                  className={`w-3 h-3 ${isRefreshing ? "animate-spin" : ""}`}
                />
                Thử lại
              </button>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* 3. RIGHT CONTROLS: SCHEMA DRAWER & ROLE BADGE */}
        {/* ================================================================= */}
        <div className="flex items-center gap-3">
          {/* Nút bật/tắt Schema Reference Drawer */}
          <button
            onClick={toggleSchemaDrawer}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isSchemaDrawerOpen
                ? "bg-brand-500/20 text-brand-300 border-brand-500/40 shadow-glow"
                : "bg-surface-subtle/60 text-slate-300 border-surface-border hover:bg-surface-subtle hover:text-white"
            }`}
            title="Mở ngăn tra cứu 8 bảng TPC-H"
          >
            <TableProperties className="w-4 h-4 text-brand-400" />
            <span className="hidden sm:inline">Tra cứu Schema</span>
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isSchemaDrawerOpen ? "bg-brand-400" : "bg-slate-500"
              }`}
            ></span>
          </button>

          {/* Bộ chuyển đổi vai trò người dùng (Component 1.3) */}
          <RoleSwitcher />
        </div>
      </div>
    </header>
  );
}
