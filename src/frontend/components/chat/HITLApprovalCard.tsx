"use client";

import React, { useState, useEffect } from "react";
import { getCurrentStoredRole } from "@/services/api";
import { UserRole } from "@/types/api";
import {
  Check,
  Loader2,
  ShieldAlert,
  X,
  AlertTriangle,
  AlertOctagon,
  Copy,
  CheckCheck,
} from "lucide-react";

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

export type RiskTier = "low" | "medium" | "high";

/**
 * Phân cấp rủi ro chi phí truy vấn dựa trên dung lượng quét dữ liệu
 */
export function getRiskTier(bytes?: number | null): RiskTier {
  if (!bytes || bytes <= 0) return "low";
  const mb = bytes / (1024 * 1024);
  if (mb < 50) return "low";
  if (mb <= 500) return "medium";
  return "high";
}

export interface HITLApprovalCardProps {
  sql?: string | null;
  estimatedBytes?: number | null;
  onApprove: () => void;
  onReject: (reason?: string) => void;
  isSubmitting?: boolean;
  className?: string;
}

const REJECTION_QUICK_CHIPS = [
  "Thiếu điều kiện lọc thời gian",
  "Quét quá nhiều dữ liệu (> 500MB)",
  "Cần tối ưu câu lệnh SQL",
];

export function HITLApprovalCard({
  sql,
  estimatedBytes,
  onApprove,
  onReject,
  isSubmitting = false,
  className = "",
}: HITLApprovalCardProps) {
  const [activeRole, setActiveRole] = useState<UserRole>(() => getCurrentStoredRole());
  const isAdmin = activeRole === "Admin";

  const handleSwitchToAdmin = () => {
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("text2sql_user_role", "Admin");
      } catch {
        // Ignore
      }
    }
    setActiveRole("Admin");
  };

  const [isRejecting, setIsRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [copied, setCopied] = useState(false);

  const riskTier = getRiskTier(estimatedBytes);
  const formattedCost = formatBytes(estimatedBytes);

  // Tính phần trăm trên hạn mức trần 1 GB (1024 MB)
  const maxBytes = 1024 * 1024 * 1024;
  const percentage = Math.min(
    100,
    Math.max(3, Math.round(((estimatedBytes || 0) / maxBytes) * 100))
  );

  const riskConfig = {
    low: {
      badgeText: "Rủi ro thấp",
      badgeStyle: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
      gaugeColor: "bg-emerald-500",
      icon: ShieldAlert,
    },
    medium: {
      badgeText: "Rủi ro trung bình",
      badgeStyle: "bg-amber-500/15 text-amber-300 border-amber-500/30",
      gaugeColor: "bg-amber-500",
      icon: AlertTriangle,
    },
    high: {
      badgeText: "Rủi ro cao (High Risk)",
      badgeStyle: "bg-rose-500/15 text-rose-400 border-rose-500/30",
      gaugeColor: "bg-rose-500",
      icon: AlertOctagon,
    },
  }[riskTier];

  const RiskIcon = riskConfig.icon;

  const handleConfirmReject = () => {
    onReject(reason.trim() || undefined);
  };

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

  // Keyboard shortcut listener: Escape để hủy từ chối
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isRejecting) {
        setIsRejecting(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRejecting]);

  return (
    <div
      className={`rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 sm:p-5 space-y-4 backdrop-blur-md transition-all shadow-sm ${className}`}
      role="region"
      aria-label="Thẻ phê duyệt truy vấn HITL"
    >
      {/* Header Bar */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
            <RiskIcon className="w-4 h-4 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold text-amber-200 tracking-wide uppercase">
                Cảnh báo chi phí truy vấn (HITL Required)
              </h4>
              {/* Risk Tier Badge */}
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border font-mono-data ${riskConfig.badgeStyle}`}
              >
                {riskConfig.badgeText}
              </span>
            </div>
            <p className="text-[11px] text-amber-300/80 mt-0.5">
              Yêu cầu Quản trị viên (Admin / Data Lead) soát xét và phê duyệt trước khi quét kho dữ liệu
            </p>
          </div>
        </div>

        {/* Cost Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/20 border border-amber-500/30 text-xs font-semibold text-amber-300 font-mono-data">
          <span>Ước lượng quét:</span>
          <span className="text-white font-bold">{formattedCost}</span>
        </div>
      </div>

      {/* Visual Cost Gauge */}
      <div className="space-y-1.5 bg-surface-primary/60 p-3 rounded-xl border border-border-default/60">
        <div className="flex items-center justify-between text-[11px] text-slate-300 font-mono-data">
          <span>Thước đo dung lượng quét (Cost Scanned Gauge)</span>
          <span className="text-slate-400">Chiếm {percentage}% định mức 1 GB</span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          className="w-full h-2 rounded-full bg-slate-800 overflow-hidden border border-slate-700/60"
        >
          <div
            className={`h-full transition-all duration-300 rounded-full ${riskConfig.gaugeColor}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      {/* SQL Preview Block */}
      {sql && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-medium text-slate-400">
            <span>Câu lệnh SQL dự kiến thực thi:</span>
            <button
              type="button"
              onClick={handleCopySql}
              className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
              title="Sao chép SQL"
            >
              {copied ? (
                <CheckCheck className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              <span>{copied ? "Đã chép" : "Sao chép"}</span>
            </button>
          </div>
          <div className="rounded-xl overflow-hidden border border-white/10 bg-[#090d18] p-3">
            <pre className="text-xs font-mono-data text-indigo-300 overflow-x-auto custom-scrollbar leading-relaxed whitespace-pre-wrap">
              <code>{sql}</code>
            </pre>
          </div>
        </div>
      )}

      {/* RBAC Governance Notice when viewing as Analyst */}
      {!isAdmin && (
        <div className="flex items-center justify-between gap-3 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-200 text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <span className="truncate">
              Tài khoản hiện tại là <span className="font-semibold text-white">Analyst</span>. Phê duyệt HITL yêu cầu quyền <span className="font-semibold text-amber-300">Admin</span>.
            </span>
          </div>
          <button
            type="button"
            onClick={handleSwitchToAdmin}
            className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 font-medium text-[11px] whitespace-nowrap transition-all shadow-sm active:scale-95 flex-shrink-0"
          >
            Chuyển sang Admin
          </button>
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
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-primary/80 hover:bg-rose-500/20 text-slate-300 hover:text-rose-200 border border-border-default/80 hover:border-rose-500/40 text-xs font-medium transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="w-3.5 h-3.5" />
            <span>Từ chối</span>
          </button>
        </div>
      ) : (
        /* Rejection Reason Input Expanded with Quick Chips */
        <div className="space-y-3 pt-1 animate-in fade-in duration-150">
          <div className="text-xs font-medium text-rose-300">
            Lý do từ chối (tùy chọn hoặc chọn nhanh bên dưới):
          </div>

          {/* Quick Suggestion Chips */}
          <div className="flex flex-wrap gap-1.5">
            {REJECTION_QUICK_CHIPS.map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setReason(chip)}
                className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 border border-rose-500/25 transition-colors"
              >
                {chip}
              </button>
            ))}
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
              className="px-3 py-1.5 rounded-lg bg-surface-primary hover:bg-surface-primary/80 text-slate-400 hover:text-slate-200 text-xs transition-all border border-border-default/60"
            >
              Hủy bỏ (Esc)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default HITLApprovalCard;
