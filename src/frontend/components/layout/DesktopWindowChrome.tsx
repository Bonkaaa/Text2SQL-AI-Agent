"use client";

import React, { useState } from "react";
import {
  Database,
  Layers,
  Minus,
  MoreHorizontal,
  Plus,
  Sparkles,
  Square,
  X,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";

export function DesktopWindowChrome() {
  const { startNewSession, showToast } = useAppContext();
  const [activeTabId, setActiveTabId] = useState("tab-agent");
  const [tabs, setTabs] = useState([
    {
      id: "tab-tpch",
      title: "TPC-H Warehouse",
      icon: Database,
      closable: false,
    },
    {
      id: "tab-duckdb",
      title: "DuckDB Engine",
      icon: Layers,
      closable: false,
    },
    {
      id: "tab-agent",
      title: "Text2SQL Agent",
      icon: Sparkles,
      closable: true,
      isActive: true,
    },
  ]);

  const handleNewTab = () => {
    startNewSession();
    showToast("Đã mở không gian phân tích mới.", "info", 2000);
  };

  const handleCloseTab = (tabId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (tabs.length <= 1) return;
    setTabs((prev) => prev.filter((t) => t.id !== tabId));
    if (activeTabId === tabId) {
      setActiveTabId(tabs[0].id);
    }
  };

  return (
    <div className="h-10 w-full bg-[#0b101d] border-b border-surface-border flex items-center justify-between px-3 select-none flex-shrink-0 z-30">
      {/* Left: Tab Bar Controls */}
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
        {/* New Tab Button (+) */}
        <button
          onClick={handleNewTab}
          className="h-6 w-6 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-surface-subtle transition-all active:scale-95"
          title="Mở tab phân tích mới"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>

        {/* Workspace Tab Pills */}
        <div className="flex items-center gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTabId === tab.id;
            return (
              <div
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                className={`group flex items-center gap-2 px-3 py-1 rounded-lg text-xs font-medium cursor-pointer transition-all duration-150 ${
                  isActive
                    ? "bg-surface-subtle text-slate-100 shadow-sm border border-white/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-subtle/50"
                }`}
              >
                <Icon
                  className={`w-3.5 h-3.5 ${
                    isActive ? "text-brand-400" : "text-slate-500"
                  }`}
                />
                <span className="truncate max-w-[120px]">{tab.title}</span>
                {tab.closable && (
                  <button
                    onClick={(e) => handleCloseTab(tab.id, e)}
                    className="p-0.5 rounded-full text-slate-500 hover:text-white hover:bg-surface transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            );
          })}

          {/* More Tabs (...) */}
          <button
            onClick={() => showToast("Quản lý phiên làm việc đa tab", "info", 1500)}
            className="h-6 w-6 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-surface-subtle transition-all"
            title="Tùy chọn tab"
          >
            <MoreHorizontal className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Right: Window Controls (Minimize, Maximize, Close) */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => showToast("Thu nhỏ cửa sổ", "info", 1000)}
          className="h-6 w-6 rounded-md flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-surface-subtle transition-all"
          title="Thu nhỏ"
        >
          <Minus className="w-3 h-3" />
        </button>
        <button
          onClick={() => showToast("Phóng to toàn màn hình", "info", 1000)}
          className="h-6 w-6 rounded-md flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-surface-subtle transition-all"
          title="Toàn màn hình"
        >
          <Square className="w-2.5 h-2.5" />
        </button>
        <button
          onClick={() => showToast("Đóng phiên", "info", 1000)}
          className="h-6 w-6 rounded-md flex items-center justify-center text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
          title="Đóng"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
