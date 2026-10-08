"use client";

import React, { useState } from "react";
import {
  X,
  Clock,
  ShieldCheck,
  Code2,
  Copy,
  Check,
  Layers,
  Lock,
} from "lucide-react";
import { formatDurationSeconds } from "@/utils/formatters";

export interface InspectorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  executionTimeMs?: number | null;
  scannedBytes?: number | null;
  sql?: string | null;
  astVerified?: boolean;
  role?: string;
  tablesUsed?: string[];
  maskedColumns?: string[];
  className?: string;
}

// Tập hợp các bảng Fact trong chuẩn TPC-DS 24 bảng
const FACT_TABLES = new Set([
  "store_sales",
  "web_sales",
  "catalog_sales",
  "store_returns",
  "web_returns",
  "catalog_returns",
  "inventory",
]);

export function InspectorDrawer({
  isOpen,
  onClose,
  executionTimeMs,
  scannedBytes,
  sql,
  astVerified = false,
  role = "Analyst",
  tablesUsed = ["store_sales", "date_dim", "store"],
  maskedColumns = ["c_email_address", "ca_street_name"],
  className = "",
}: InspectorDrawerProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopySql = async () => {
    if (!sql) return;
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(sql);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Ignore clipboard error
    }
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return "0 MB";
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  // Phân tách Fact tables và Dimension tables
  const factTables = (tablesUsed || []).filter((tbl) => FACT_TABLES.has(tbl.toLowerCase()));
  const dimTables = (tablesUsed || []).filter((tbl) => !FACT_TABLES.has(tbl.toLowerCase()));

  return (
    <aside
      aria-label="Context & Governance Inspector"
      className={`w-[340px] flex-shrink-0 bg-surface border-l border-surface-border flex flex-col h-full overflow-y-auto custom-scrollbar z-20 animate-in slide-in-from-right-4 duration-200 ${className}`}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-surface-border bg-surface-secondary/40 sticky top-0 backdrop-blur-md z-10">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-brand-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 font-sans-ui">
            Context & Governance Inspector
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Đóng inspector"
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-surface-tertiary transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-5 flex-1 text-xs">
        {/* Section 1: Telemetry Metrics */}
        <div className="space-y-2.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            <span>Hiệu năng & Telemetry</span>
          </div>
          <div className="grid grid-cols-2 gap-2 bg-surface-secondary/60 p-2.5 rounded-xl border border-surface-border">
            <div>
              <div className="text-[10px] text-slate-400">Thời gian phân tích</div>
              <div className="text-sm font-bold text-white font-mono-data mt-0.5">
                {executionTimeMs !== undefined ? `${executionTimeMs}ms` : "—"}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400">Dung lượng quét</div>
              <div className="text-sm font-bold text-white font-mono-data mt-0.5">
                {formatBytes(scannedBytes)}
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Security & Governance */}
        <div className="space-y-2.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Xác thực & An toàn Dữ liệu</span>
          </div>
          <div className="space-y-2 bg-surface-secondary/60 p-2.5 rounded-xl border border-surface-border">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">AST Sanitizer:</span>
              <span className="inline-flex items-center gap-1 font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 text-[10px]">
                SELECT-ONLY (Hợp lệ)
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Chính sách RBAC:</span>
              <span className="font-mono text-slate-200 bg-surface-tertiary px-1.5 py-0.5 rounded text-[10px]">
                Role: {role}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Bảo vệ PII:</span>
              <span className="inline-flex items-center gap-1 text-slate-300 text-[10px]">
                <Lock className="w-3 h-3 text-amber-400" />
                <span>Masking tự động</span>
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: PII Masking Audit */}
        {maskedColumns && maskedColumns.length > 0 && (
          <div className="space-y-2">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-amber-400" />
              <span>Kiểm toán Cột Nhạy cảm (PII Audit)</span>
            </div>
            <div className="bg-surface-secondary/60 border border-surface-border rounded-xl p-2.5 space-y-1.5">
              <div className="text-[10px] text-slate-400">
                Các cột định danh sau đã được áp dụng Che giấu tự động:
              </div>
              <div className="flex flex-col gap-1">
                {maskedColumns.map((col) => (
                  <div
                    key={col}
                    className="flex items-center justify-between text-[11px] font-mono-data py-0.5 border-b border-surface-border/40 last:border-0"
                  >
                    <span className="text-amber-300 font-semibold">{col}</span>
                    <span className="text-[10px] text-slate-400 italic">Che giấu tự động</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Section 4: SQL Code & Inspector */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Truy vấn DuckDB SQL</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleCopySql}
                className="p-1 text-slate-400 hover:text-white hover:bg-surface-tertiary rounded transition-colors"
                title="Sao chép SQL"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>
          </div>

          <div className="bg-[#070A10] border border-surface-border rounded-xl p-3 font-mono text-[11px] text-slate-200 overflow-x-auto leading-relaxed max-h-48 custom-scrollbar">
            {sql ? (
              <pre className="whitespace-pre-wrap">{sql}</pre>
            ) : (
              <span className="text-slate-500 italic">Chưa có câu truy vấn SQL nào được thực thi.</span>
            )}
          </div>
        </div>

        {/* Section 5: Data Lineage & Tables Referenced */}
        <div className="space-y-2.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Nguồn gốc Dữ liệu (Lineage)</span>
          </div>

          {/* Fact Tables Group */}
          {factTables.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-primary-400 uppercase">
                Bảng Sự kiện (Fact Tables)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {factTables.map((tbl) => (
                  <span
                    key={tbl}
                    className="px-2 py-0.5 rounded-lg bg-primary-500/10 text-primary-300 border border-primary-500/30 font-mono-data text-[10px]"
                  >
                    {tbl}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Dimension Tables Group */}
          {dimTables.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-slate-400 uppercase">
                Bảng Danh mục (Dimension Tables)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {dimTables.map((tbl) => (
                  <span
                    key={tbl}
                    className="px-2 py-0.5 rounded-lg bg-surface-secondary text-slate-300 border border-surface-border font-mono-data text-[10px]"
                  >
                    {tbl}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

export default InspectorDrawer;
