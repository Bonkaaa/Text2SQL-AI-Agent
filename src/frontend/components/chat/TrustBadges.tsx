"use client";

import React from "react";
import { ShieldCheck, Users, Lock, Zap } from "lucide-react";

export interface TrustBadgesProps {
  astVerified?: boolean;
  rbacEnforced?: boolean;
  role?: string;
  piiProtected?: boolean;
  costBytes?: number | null;
  className?: string;
}

export const TrustBadges: React.FC<TrustBadgesProps> = ({
  astVerified = false,
  rbacEnforced = false,
  role,
  piiProtected = false,
  costBytes,
  className = "",
}) => {
  // Nếu không có cờ an toàn nào được bật thì không render
  const hasBadges = astVerified || rbacEnforced || piiProtected || (costBytes != null && costBytes > 0);

  if (!hasBadges) {
    return null;
  }

  return (
    <div className={`flex items-center flex-wrap gap-1.5 ${className}`}>
      {/* 1. AST Sanitizer Badge */}
      {astVerified && (
        <span
          title="AST Sanitizer: Đã kiểm duyệt cây cú pháp Abstract Syntax Tree, bảo đảm 100% câu truy vấn chỉ đọc (SELECT-only), chặn đứng tuyệt đối DDL/DML."
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono-data font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm cursor-help"
        >
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span>AST Sanitized</span>
        </span>
      )}

      {/* 2. RBAC Policy Enforcement Badge */}
      {rbacEnforced && (
        <span
          title={`RBAC Enforced: Đã áp dụng chính sách phân quyền truy cập theo vai trò (${role || "Standard"}). Các bảng và trường hạn chế đã được cô lập.`}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono-data font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-sm cursor-help"
        >
          <Users className="w-3 h-3 text-blue-400" />
          <span>{role ? `RBAC: ${role}` : "RBAC Enforced"}</span>
        </span>
      )}

      {/* 3. PII Masking Protection Badge */}
      {piiProtected && (
        <span
          title="PII Protected: Tự động phát hiện và che giấu/mã hóa các trường định danh cá nhân nhạy cảm (Email, Họ tên, Địa chỉ khách hàng)."
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono-data font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-sm cursor-help"
        >
          <Lock className="w-3 h-3 text-amber-400" />
          <span>PII Protected</span>
        </span>
      )}

      {/* 4. Cost Guard Budget Badge */}
      {costBytes != null && costBytes > 0 && (
        <span
          title={`Cost Guard: Dung lượng quét dự kiến ${Math.round(costBytes / 1024)} KB nằm trong hạn mức ngân sách cho phép.`}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono-data font-medium bg-slate-800 text-slate-300 border border-slate-700/60 shadow-sm cursor-help"
        >
          <Zap className="w-3 h-3 text-violet-400" />
          <span>Cost Guard</span>
        </span>
      )}
    </div>
  );
};

export default TrustBadges;
