"use client";

import React, { useState } from "react";
import { Check, Loader2, ShieldAlert, X } from "lucide-react";

export function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "0 B";
  if (bytes >= 1048576) {
    return `${(bytes / 1048576).toFixed(1)} MB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${bytes} B`;
}

export interface HITLApprovalCardProps {
  sql?: string | null;
  estimatedBytes?: number | null;
  onApprove: () => void;
  onReject: (reason?: string) => void;
  isSubmitting?: boolean;
  className?: string;
}

export function HITLApprovalCard({
  sql,
  estimatedBytes,
  onApprove,
  onReject,
  isSubmitting = false,
  className = "",
}: HITLApprovalCardProps) {
  const [isRejecting, setIsRejecting] = useState(false);
  const [reason, setReason] = useState("");

  const handleConfirmReject = () => {
    onReject(reason.trim() || undefined);
  };

  const formattedCost = formatBytes(estimatedBytes);

  return (
    <div
      className={`rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 sm:p-5 space-y-4 backdrop-blur-md transition-all ${className}`}
      role="region"
      aria-label="Thẻ phê duyệt truy vấn HITL"
    >
      {/* Header Bar */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-amber-200 tracking-wide uppercase">
              Cảnh báo chi phí truy vấn (HITL Required)
            </h4>
            <p className="text-[11px] text-amber-300/80 mt-0.5">
              Yêu cầu con người soát xét trước khi quét bảng dữ liệu lớn
            </p>
          </div>
        </div>

        {/* Cost Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/20 border border-amber-500/30 text-xs font-semibold text-amber-300 font-mono">
          <span>Ước lượng quét:</span>
          <span className="text-white font-bold">{formattedCost}</span>
        </div>
      </div>

      {/* SQL Preview Block */}
      {sql && (
        <div className="space-y-1.5">
          <div className="text-[11px] font-medium text-slate-400">
            Câu lệnh SQL dự kiến thực thi:
          </div>
          <div className="rounded-xl overflow-hidden border border-white/10 bg-[#090d18] p-3">
            <pre className="text-xs font-mono text-indigo-300 overflow-x-auto custom-scrollbar leading-relaxed whitespace-pre-wrap">
              <code>{sql}</code>
            </pre>
          </div>
        </div>
      )}

      {/* Action Buttons & Rejection Form */}
      {!isRejecting ? (
        <div className="flex items-center gap-2.5 pt-1">
          {/* Approve Button */}
          <button
            type="button"
            disabled={isSubmitting}
            onClick={onApprove}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
            <span>Phê duyệt & Thực thi</span>
          </button>

          {/* Reject Trigger Button */}
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => setIsRejecting(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-subtle/80 hover:bg-rose-500/20 text-slate-300 hover:text-rose-200 border border-surface-border hover:border-rose-500/40 text-xs font-medium transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="w-3.5 h-3.5" />
            <span>Từ chối</span>
          </button>
        </div>
      ) : (
        /* Rejection Reason Input Expanded */
        <div className="space-y-2.5 pt-1 animate-in fade-in duration-150">
          <div className="text-xs font-medium text-rose-300">
            Lý do từ chối (tùy chọn):
          </div>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={isSubmitting}
            placeholder="Nhập lý do từ chối câu truy vấn này..."
            className="w-full bg-[#121624] border border-rose-500/30 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder:text-slate-500 outline-none focus:ring-1 focus:ring-rose-400"
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleConfirmReject}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-all disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <X className="w-3 h-3" />
              )}
              <span>Xác nhận từ chối</span>
            </button>
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => setIsRejecting(false)}
              className="px-3 py-1.5 rounded-lg bg-surface-subtle hover:bg-surface-subtle/80 text-slate-400 hover:text-slate-200 text-xs transition-all"
            >
              Hủy bỏ
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default HITLApprovalCard;
