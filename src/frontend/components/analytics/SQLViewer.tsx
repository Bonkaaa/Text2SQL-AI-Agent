"use client";

import React, { useState } from "react";
import {
  Code2,
  Copy,
  Check,
  WrapText,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import { useOptionalAppContext } from "@/context/AppContext";

export interface SQLViewerProps {
  sql: string;
  title?: string;
  showLineNumbers?: boolean;
  allowWrapToggle?: boolean;
  className?: string;
  onCopy?: () => void;
}

export function SQLViewer({
  sql,
  title = "Truy vấn SQL đã thực thi",
  showLineNumbers = true,
  allowWrapToggle = true,
  className = "",
  onCopy,
}: SQLViewerProps) {
  const appContext = useOptionalAppContext();
  const [isWrap, setIsWrap] = useState(false);
  const [copied, setCopied] = useState(false);

  // Xử lý khi câu SQL rỗng
  if (!sql || !sql.trim()) {
    return (
      <div
        className={`rounded-2xl border border-surface-border bg-[#0a0f1d]/80 p-6 text-center text-slate-400 text-xs backdrop-blur-md ${className}`}
        role="region"
        aria-label="Khối xem câu lệnh SQL"
      >
        <Terminal className="w-6 h-6 text-slate-500 mx-auto mb-1.5" />
        <span>Không có câu lệnh SQL</span>
      </div>
    );
  }

  const lines = sql.split("\n");

  const handleCopy = async () => {
    onCopy?.();
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(sql);
        setCopied(true);
        appContext?.showToast("Đã sao chép câu lệnh SQL vào clipboard", "success", 2000);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Bỏ qua lỗi clipboard trong môi trường bảo mật
    }
  };

  return (
    <div
      className={`rounded-2xl border border-surface-border bg-[#0a0f1d]/90 p-4 sm:p-5 space-y-3.5 backdrop-blur-md shadow-card transition-all ${className}`}
      role="region"
      aria-label="Khối xem câu lệnh SQL"
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-3 flex-wrap border-b border-surface-border pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-brand-500/15 border border-brand-500/25 flex items-center justify-center flex-shrink-0">
            <Code2 className="w-4 h-4 text-brand-400" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200 tracking-wide uppercase">
              {title}
            </h4>
          </div>
        </div>

        {/* Badges & Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Badge AST Verified */}
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 font-medium flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>AST Verified</span>
          </span>

          {/* Badge Số dòng */}
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-subtle text-slate-400 border border-surface-border font-mono font-medium">
            {lines.length} dòng
          </span>

          {/* Wrap Text Toggle */}
          {allowWrapToggle && (
            <button
              type="button"
              onClick={() => setIsWrap(!isWrap)}
              aria-pressed={isWrap}
              aria-label="Bọc dòng"
              title={isWrap ? "Tắt bọc dòng (Cuộn ngang)" : "Bật bọc dòng tự động"}
              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-colors border ${
                isWrap
                  ? "bg-brand-500/20 text-brand-300 border-brand-500/40"
                  : "bg-surface-subtle hover:bg-surface-subtle/80 text-slate-400 hover:text-slate-200 border-surface-border"
              }`}
            >
              <WrapText className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Bọc dòng</span>
            </button>
          )}

          {/* Copy SQL Button */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-300 bg-surface-subtle hover:bg-surface-subtle/80 hover:text-white transition-all border border-surface-border active:scale-[0.98]"
            aria-label={copied ? "Đã chép" : "Sao chép SQL"}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-semibold">Đã chép</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-400" />
                <span>Sao chép SQL</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Code Display Canvas */}
      <div className="relative rounded-xl border border-surface-border/80 bg-[#070b14] p-3.5 flex font-mono text-xs overflow-hidden">
        {/* Line Numbers Gutter */}
        {showLineNumbers && (
          <div
            data-testid="sql-line-numbers"
            className="select-none text-slate-600 border-r border-slate-800/80 pr-3 mr-3 text-right flex flex-col font-mono text-xs leading-relaxed"
            aria-hidden="true"
          >
            {lines.map((_, idx) => (
              <span key={idx}>{idx + 1}</span>
            ))}
          </div>
        )}

        {/* Code Pre/Code Area */}
        <pre
          className={`text-indigo-300 flex-1 leading-relaxed custom-scrollbar font-mono text-xs ${
            isWrap
              ? "whitespace-pre-wrap break-all"
              : "whitespace-pre overflow-x-auto"
          }`}
        >
          <code>{sql}</code>
        </pre>
      </div>
    </div>
  );
}

export default SQLViewer;
