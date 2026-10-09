"use client";

import React, { useState } from "react";
import { Check, Copy, ShieldCheck, Database, Lock } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";

interface SQLViewerProps {
  sql: string;
  dialect?: string;
  isAstVerified?: boolean;
}

export function SQLViewer({
  sql,
  dialect = "duckdb",
  isAstVerified = true,
}: SQLViewerProps) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!sql) return;
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const lines = (sql || "").trim().split("\n");

  return (
    <div className="space-y-3">
      {/* Header Badges & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {/* AST Verified Badge */}
          {isAstVerified && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-soft text-emerald border border-emerald/20">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{t("workspace.astVerified")}</span>
            </span>
          )}

          {/* Read-Only Badge */}
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-surface-2 text-muted border border-line">
            <Lock className="w-3 h-3" />
            <span>{t("workspace.readOnlyGuaranteed")}</span>
          </span>

          {/* Dialect */}
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-surface-2 text-muted border border-line">
            <Database className="w-3 h-3 text-primary" />
            <span className="uppercase">{dialect}</span>
          </span>
        </div>

        {/* Copy SQL Button */}
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 text-foreground transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald" />
              <span className="text-emerald">{t("workspace.copied")}</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-muted" />
              <span>{t("workspace.copySql")}</span>
            </>
          )}
        </button>
      </div>

      {/* Code Display Canvas */}
      <div className="border border-line rounded-xl bg-slate-900 text-slate-100 overflow-hidden shadow-card font-mono text-xs">
        <div className="flex items-center justify-between px-3.5 py-2 border-b border-slate-800 bg-slate-950/60 text-[10px] text-slate-400">
          <span>query.sql</span>
          <span>
            {lines.length} {t("workspace.lines")}
          </span>
        </div>
        <div className="p-4 overflow-x-auto">
          <pre className="grid grid-cols-[auto,1fr] gap-x-4 font-mono leading-relaxed select-text">
            {lines.map((line, idx) => (
              <React.Fragment key={idx}>
                <span className="text-slate-600 text-right select-none tabular-nums text-[11px]">
                  {idx + 1}
                </span>
                <span className="text-slate-200 whitespace-pre">
                  {line}
                </span>
              </React.Fragment>
            ))}
          </pre>
        </div>
      </div>
    </div>
  );
}
