"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  Database,
  Layers,
  RefreshCw,
  Sparkles,
  TableProperties,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";

export function Header() {
  const {
    health,
    refreshHealth,
    isSchemaDrawerOpen,
    toggleSchemaDrawer,
    showToast,
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
    <header className="sticky top-0 z-40 w-full border-b border-surface-border bg-[#0b101d]/90 backdrop-blur-md transition-colors flex-shrink-0">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        {/* ================================================================= */}
        {/* LEFT: ENGINE / MODEL SELECTOR PILL (like "iBeeBot 4o ⌄" in image) */}
        {/* ================================================================= */}
        <div className="flex items-center gap-3">
          {/* Model Selector Dropdown Pill */}
          <div className="relative">
            <button
              onClick={() => setEngineMenuOpen(!isEngineMenuOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-subtle/80 hover:bg-surface-subtle border border-surface-border text-xs font-semibold text-slate-200 transition-all shadow-sm active:scale-98"
            >
              <div className="w-4 h-4 rounded-md bg-gradient-to-tr from-brand-500 to-indigo-400 flex items-center justify-center text-white flex-shrink-0">
                <Sparkles className="w-2.5 h-2.5" />
              </div>
              <span>DeepAgents TPC-H 4o</span>
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
              <div className="absolute top-full left-0 mt-1.5 w-64 p-3 rounded-2xl bg-[#0f172a] border border-surface-border shadow-card z-50 animate-in fade-in slide-in-from-top-2 duration-150 space-y-2.5">
                <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                  Cấu hình AI Agent
                </div>

                <div className="space-y-1.5 text-xs text-slate-300">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-surface-subtle/60">
                    <span className="text-slate-400">Warehouse:</span>
                    <span className="font-semibold text-slate-200">DuckDB TPC-H</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-surface-subtle/60">
                    <span className="text-slate-400">Trạng thái:</span>
                    <span
                      className={`font-semibold ${
                        health.isConnected ? "text-emerald-400" : "text-amber-400"
                      }`}
                    >
                      {health.isConnected ? "Sẵn sàng (200 OK)" : "Đang kiểm tra"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-surface-subtle/60">
                    <span className="text-slate-400">Độ trễ:</span>
                    <span className="font-mono text-slate-200">
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
        {/* RIGHT: SCHEMA DRAWER TOGGLE                                      */}
        {/* ================================================================= */}
        <div className="flex items-center gap-2.5">
          {/* Schema Drawer Toggle Button */}
          <button
            onClick={toggleSchemaDrawer}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isSchemaDrawerOpen
                ? "bg-brand-500/20 text-brand-300 border-brand-500/40"
                : "bg-surface-subtle/60 text-slate-300 border-surface-border hover:bg-surface-subtle hover:text-white"
            }`}
            title="Tra cứu 8 bảng TPC-H"
          >
            <TableProperties className="w-3.5 h-3.5 text-brand-400" />
            <span>Schema</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface text-slate-400 font-mono ml-0.5">
              8
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
