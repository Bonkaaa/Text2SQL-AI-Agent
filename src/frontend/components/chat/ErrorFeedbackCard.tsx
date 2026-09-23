"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  ShieldAlert,
  Clock,
  Terminal,
} from "lucide-react";

export interface ErrorTypeConfig {
  label: string;
  description: string | null;
  badgeClass: string;
  icon: React.ComponentType<{ className?: string }>;
}

export function getErrorTypeDetails(errorType?: string): ErrorTypeConfig {
  switch (errorType) {
    case "RBAC_VIOLATION":
      return {
        label: "Chính sách bảo mật (RBAC)",
        description:
          "Bạn không có quyền truy cập trường dữ liệu nhạy cảm hoặc bảng bảo mật theo phân quyền vai trò hiện tại.",
        badgeClass: "bg-rose-500/20 text-rose-300 border-rose-500/30",
        icon: ShieldAlert,
      };
    case "AST_BLOCKED":
      return {
        label: "Chặn bởi AST Sanitizer",
        description:
          "Truy vấn chứa từ khóa không an toàn hoặc cấu trúc SQL bị cấm (hệ thống chỉ chấp thuận truy vấn đọc SELECT).",
        badgeClass: "bg-amber-500/20 text-amber-300 border-amber-500/30",
        icon: AlertTriangle,
      };
    case "TIMEOUT":
      return {
        label: "Quá thời gian thực thi (Timeout)",
        description:
          "Thời gian thực thi truy vấn vượt quá ngưỡng phản hồi tối đa cho phép của kho dữ liệu DuckDB.",
        badgeClass: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
        icon: Clock,
      };
    default:
      return {
        label: "Lỗi thực thi truy vấn",
        description: null,
        badgeClass: "bg-rose-500/20 text-rose-300 border-rose-500/30",
        icon: AlertTriangle,
      };
  }
}

export interface ErrorFeedbackCardProps {
  errorMessage: string;
  errorType?: string;
  retryCount?: number;
  maxRetries?: number;
  onRetry?: () => void;
  className?: string;
}

export function ErrorFeedbackCard({
  errorMessage,
  errorType,
  retryCount,
  maxRetries = 3,
  onRetry,
  className = "",
}: ErrorFeedbackCardProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(false);

  const errorConfig = getErrorTypeDetails(errorType);
  const ErrorIcon = errorConfig.icon;

  const handleCopy = async () => {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(errorMessage);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Ignore clipboard write failures in restricted environments
    }
  };

  return (
    <div
      className={`rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 sm:p-5 space-y-4 backdrop-blur-md transition-all ${className}`}
      role="region"
      aria-label="Thẻ thông báo lỗi thực thi"
    >
      {/* Header Bar */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center flex-shrink-0">
            <ErrorIcon className="w-4 h-4 text-rose-400" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-rose-200 tracking-wide uppercase">
              Không thể hoàn tất truy vấn
            </h4>
            <p className="text-[11px] text-rose-300/80 mt-0.5">
              Đã xảy ra sự cố trong quá trình xử lý hoặc thẩm định an toàn
            </p>
          </div>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {errorType && (
            <span
              className={`text-[10px] px-2.5 py-0.5 rounded-full border font-semibold ${errorConfig.badgeClass}`}
            >
              {errorConfig.label}
            </span>
          )}

          {retryCount !== undefined && retryCount > 0 && (
            <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-rose-500/25 border border-rose-500/40 text-rose-200 font-mono font-medium flex items-center gap-1">
              <RotateCcw className="w-3 h-3 text-rose-300" />
              <span>
                Tự sửa lỗi: {retryCount}/{maxRetries} lần thất bại
              </span>
            </span>
          )}
        </div>
      </div>

      {/* Friendly Description / Message */}
      <div className="space-y-1.5 text-xs text-rose-200 leading-relaxed bg-surface/50 p-3.5 rounded-xl border border-rose-500/20">
        {errorConfig.description && (
          <p className="font-medium text-rose-300 mb-1">
            {errorConfig.description}
          </p>
        )}
        <p className="text-rose-200/90 font-mono text-[11px] break-words">
          {errorMessage}
        </p>
      </div>

      {/* Actions & Accordion Trigger */}
      <div className="flex items-center justify-between gap-3 flex-wrap pt-1 border-t border-rose-500/20">
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center gap-1.5 text-xs font-medium text-rose-300 hover:text-rose-100 transition-colors"
          aria-expanded={showDetails}
          aria-label="Chi tiết kỹ thuật"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Chi tiết kỹ thuật</span>
          {showDetails ? (
            <ChevronUp className="w-3.5 h-3.5 ml-0.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 ml-0.5" />
          )}
        </button>

        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 hover:text-white border border-rose-500/40 text-xs font-semibold shadow-sm transition-all active:scale-[0.98]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Thử lại</span>
          </button>
        )}
      </div>

      {/* Accordion Content: Technical Details & Copy */}
      {showDetails && (
        <div className="space-y-2 pt-2 animate-in fade-in duration-200">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Chi tiết lỗi từ máy chủ:</span>
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-surface-subtle hover:bg-surface-subtle/80 text-slate-300 hover:text-white transition-colors border border-surface-border text-[10px]"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400">Đã chép</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Sao chép</span>
                </>
              )}
            </button>
          </div>
          <pre className="p-3 rounded-xl bg-[#0a0f1d] border border-surface-border text-[11px] font-mono text-rose-300 overflow-x-auto custom-scrollbar leading-relaxed whitespace-pre-wrap break-all">
            <code>{errorMessage}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
