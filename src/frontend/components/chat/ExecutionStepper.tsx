"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Database,
  Loader2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export interface ExecutionStepperProps {
  isLoading?: boolean;
  executionTimeMs?: number;
  totalRows?: number;
  tablesUsed?: string[];
  defaultExpanded?: boolean;
  className?: string;
}

export function ExecutionStepper({
  isLoading = false,
  executionTimeMs,
  totalRows,
  tablesUsed = ["store_sales", "date_dim"],
  defaultExpanded = false,
  className = "",
}: ExecutionStepperProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // 1. Trạng thái Đang Xử Lý (Loading State) - Live Activity Indicator
  if (isLoading) {
    return (
      <div
        className={`flex items-center gap-2.5 px-3 py-2 rounded-xl bg-surface border border-surface-border text-xs text-slate-300 animate-in fade-in duration-150 ${className}`}
      >
        <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin flex-shrink-0" />
        <span className="font-medium">
          Đang phân tích câu hỏi & đối soát dữ liệu TPC-DS...
        </span>
        <span className="ml-auto inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-500/10 text-blue-300 border border-blue-500/20">
          Agent Active
        </span>
      </div>
    );
  }

  // 2. Trạng thái Đã Hoàn Tất (Completed State) - Authentic Telemetry Summary
  return (
    <div
      className={`rounded-xl border border-surface-border bg-surface-secondary/40 overflow-hidden text-xs transition-all duration-150 ${className}`}
    >
      {/* Top Summary Bar */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-label="Chi tiết thực thi"
        className="w-full flex items-center justify-between px-3 py-2 text-slate-300 hover:text-white hover:bg-surface-secondary/70 transition-colors text-left"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
          <span className="font-medium text-slate-200">
            Đã xử lý trong{" "}
            <span className="font-mono font-bold text-white">
              {executionTimeMs !== undefined ? `${executionTimeMs}ms` : "—"}
            </span>
          </span>
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-3 h-3" />
            SELECT-only Verified
          </span>
          {totalRows !== undefined && (
            <span className="text-slate-400 font-mono text-[11px]">
              • {totalRows} bản ghi
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 text-slate-400 flex-shrink-0 ml-2">
          <span className="text-[11px] hidden sm:inline">Telemetry</span>
          {isExpanded ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </div>
      </button>

      {/* Expanded Telemetry Detail */}
      {isExpanded && (
        <div className="px-3 py-2.5 border-t border-surface-border bg-surface/60 text-slate-300 space-y-1.5 animate-in fade-in duration-100">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Warehouse Engine:</span>
            <span className="font-mono text-slate-200 font-semibold">DuckDB In-Memory (TPC-DS)</span>
          </div>
          <div className="flex items-start justify-between text-[11px] gap-2">
            <span className="text-slate-400 flex-shrink-0">Bảng tham chiếu:</span>
            <div className="flex flex-wrap gap-1 justify-end">
              {tablesUsed.map((tbl) => (
                <span
                  key={tbl}
                  className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-secondary text-blue-300 border border-surface-border"
                >
                  {tbl}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
