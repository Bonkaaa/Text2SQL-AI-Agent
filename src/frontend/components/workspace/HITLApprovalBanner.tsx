"use client";

import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";

interface HITLApprovalBannerProps {
  estimatedCostBytes?: number;
  sql?: string;
  onApprove: (approved: boolean, reason?: string) => void;
  isApproving: boolean;
}

export function HITLApprovalBanner({
  estimatedCostBytes,
  sql,
  onApprove,
  isApproving,
}: HITLApprovalBannerProps) {
  const { t } = useLanguage();
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);

  const formattedCost = estimatedCostBytes
    ? `${(estimatedCostBytes / (1024 * 1024)).toFixed(1)} MB`
    : "High cost";

  return (
    <div className="bg-amber-soft/80 border border-amber/40 rounded-xl p-3.5 space-y-3 mt-2 shadow-sm">
      <div className="flex items-start gap-2.5">
        <AlertTriangle className="w-4 h-4 text-amber shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <strong className="text-xs font-bold text-foreground block">
            {t("workspace.hitlTitle")}
          </strong>
          <p className="text-[11px] text-muted mt-0.5 leading-relaxed">
            {t("workspace.hitlDesc")} ({formattedCost})
          </p>
        </div>
      </div>

      {sql && (
        <pre className="p-2.5 rounded-lg bg-surface border border-line text-[10px] font-mono text-foreground overflow-x-auto max-h-24 leading-relaxed">
          {sql}
        </pre>
      )}

      {showRejectInput && (
        <div className="space-y-1.5 pt-1">
          <input
            type="text"
            placeholder={t("workspace.hitlRejectPlaceholder")}
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-line bg-surface text-xs outline-none focus:border-rose text-foreground"
          />
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={() => onApprove(true)}
          disabled={isApproving}
          aria-label="Phê duyệt"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[var(--green)] hover:bg-[#126b4a] text-white shadow-sm transition disabled:opacity-50"
        >
          {isApproving ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <CheckCircle2 className="w-3.5 h-3.5" />
          )}
          {t("workspace.hitlApprove")}
        </button>

        {!showRejectInput ? (
          <button
            type="button"
            onClick={() => setShowRejectInput(true)}
            disabled={isApproving}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-surface hover:bg-surface-2 text-rose border border-rose/30 transition disabled:opacity-50"
          >
            <XCircle className="w-3.5 h-3.5" />
            {t("workspace.hitlReject")}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onApprove(false, rejectReason || undefined)}
            disabled={isApproving}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-rose hover:bg-rose-600 text-white transition disabled:opacity-50"
          >
            {t("workspace.hitlConfirmReject")}
          </button>
        )}
      </div>
    </div>
  );
}
