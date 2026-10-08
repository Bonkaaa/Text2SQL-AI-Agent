"use client";

import React from "react";
import {
  Info,
  AlertTriangle,
  AlertCircle,
  Inbox,
} from "lucide-react";
import type { CalloutArtifact } from "../../types/artifacts";

interface CalloutCardProps {
  artifact: CalloutArtifact;
}

export const CalloutCard: React.FC<CalloutCardProps> = ({ artifact }) => {
  const { variant = "info", message } = artifact;

  const config = {
    info: {
      border: "border-primary-500/30",
      bg: "bg-primary-500/10",
      text: "text-primary-200",
      icon: Info,
      iconColor: "text-primary-400",
      title: "Thông tin lưu ý",
    },
    warning: {
      border: "border-amber-500/30",
      bg: "bg-amber-500/10",
      text: "text-amber-200",
      icon: AlertTriangle,
      iconColor: "text-amber-400",
      title: "Cảnh báo nghiệp vụ",
    },
    error: {
      border: "border-rose-500/30",
      bg: "bg-rose-500/10",
      text: "text-rose-200",
      icon: AlertCircle,
      iconColor: "text-rose-400",
      title: "Thông báo lỗi",
    },
    no_data: {
      border: "border-slate-700/60",
      bg: "bg-slate-800/40",
      text: "text-slate-300",
      icon: Inbox,
      iconColor: "text-slate-400",
      title: "Không có dữ liệu",
    },
  }[variant] || {
    border: "border-slate-700/60",
    bg: "bg-slate-800/40",
    text: "text-slate-300",
    icon: Info,
    iconColor: "text-slate-400",
    title: "Thông báo",
  };

  const Icon = config.icon;

  return (
    <div
      className={`flex items-start gap-3 p-3.5 rounded-xl border ${config.border} ${config.bg} backdrop-blur-sm text-xs leading-relaxed`}
      role="alert"
    >
      <Icon className={`w-4 h-4 ${config.iconColor} shrink-0 mt-0.5`} />
      <div className="flex-1 space-y-0.5">
        <span className="font-semibold block text-[11px] uppercase tracking-wider opacity-80">
          {config.title}
        </span>
        <p className={config.text}>{message}</p>
      </div>
    </div>
  );
};
