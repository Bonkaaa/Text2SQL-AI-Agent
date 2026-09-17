"use client";

import React from "react";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import { useAppContext } from "@/context/AppContext";

export function ToastContainer() {
  const { toasts, removeToast } = useAppContext();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full"
    >
      {toasts.map((toast) => {
        let icon = <Info className="w-5 h-5 text-brand-400 flex-shrink-0" />;
        let borderColor = "border-brand-500/30";
        let bgColor = "bg-surface/95";

        if (toast.type === "success") {
          icon = <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />;
          borderColor = "border-success/30";
        } else if (toast.type === "warning") {
          icon = (
            <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0" />
          );
          borderColor = "border-warning/30";
        } else if (toast.type === "error") {
          icon = <XCircle className="w-5 h-5 text-danger flex-shrink-0" />;
          borderColor = "border-danger/30";
        }

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl shadow-card backdrop-blur-md border ${borderColor} ${bgColor} transition-all duration-300 animate-in fade-in slide-in-from-bottom-2`}
          >
            {icon}
            <div className="flex-1 text-xs text-slate-200 leading-relaxed font-medium">
              {toast.message}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-white transition-colors p-0.5 rounded-md hover:bg-surface-subtle"
              title="Đóng"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
