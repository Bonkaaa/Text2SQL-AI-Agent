"use client";

import React from "react";
import { Sparkles, CheckCircle2, Clock, Loader2 } from "lucide-react";
import { WorkspaceMessage } from "@/hooks/useWorkspace";
import { formatCurrency, formatDuration } from "@/lib/formatters";
import { useLanguage } from "@/context/LanguageContext";

interface MessageItemProps {
  message: WorkspaceMessage;
}

export function MessageItem({ message }: MessageItemProps) {
  const { t } = useLanguage();

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-primary-soft text-foreground p-3 rounded-2xl rounded-tr-sm text-xs leading-relaxed border border-primary/20 shadow-sm font-medium">
          {message.content}
        </div>
      </div>
    );
  }

  const queryResponse = message.queryResponse;
  const kpiArtifact = queryResponse?.response_package?.artifacts?.find(
    (a) => a.type === "kpi"
  ) as any;

  return (
    <div className="space-y-2">
      {/* Header Meta */}
      <div className="flex items-center gap-1.5 text-[10px] text-muted">
        <div className="w-5 h-5 rounded bg-primary-soft text-primary grid place-items-center shrink-0">
          <Sparkles className="w-3 h-3" />
        </div>
        <strong className="text-foreground">QueryPilot Agent</strong>
        <span>·</span>
        <span>{message.timestamp}</span>
        {queryResponse?.execution_time_ms ? (
          <>
            <span>·</span>
            <span className="inline-flex items-center gap-1 font-mono text-faint">
              <Clock className="w-2.5 h-2.5" />
              {formatDuration(queryResponse.execution_time_ms)} {t("workspace.totalTime")}
            </span>
          </>
        ) : null}
      </div>

      {/* Message Body */}
      <div className="bg-surface-2 border border-line rounded-xl p-3.5 space-y-3 text-xs leading-relaxed">
        {message.isLoading ? (
          <div className="flex items-center gap-2 text-muted py-2">
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <span>{t("workspace.analyzingLoading")}</span>
          </div>
        ) : (
          <p className="text-foreground whitespace-pre-line leading-relaxed m-0">
            {message.content}
          </p>
        )}

        {/* Inline KPI Stat Row if available */}
        {kpiArtifact && (
          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="bg-surface border border-line rounded-lg p-2.5">
              <span className="block text-[10px] text-muted">{kpiArtifact.title}</span>
              <strong className="block text-base font-bold text-foreground mt-0.5 font-mono tabular-nums">
                {kpiArtifact.unit === "USD"
                  ? formatCurrency(kpiArtifact.value)
                  : `${kpiArtifact.value} ${kpiArtifact.unit || ""}`}
              </strong>
            </div>
            {queryResponse?.data && queryResponse.data.length > 0 && (
              <div className="bg-surface border border-line rounded-lg p-2.5">
                <span className="block text-[10px] text-muted">{t("workspace.returnedRecords")}</span>
                <strong className="block text-base font-bold text-foreground mt-0.5 font-mono tabular-nums">
                  {queryResponse.data.length} {t("common.rows")}
                </strong>
              </div>
            )}
          </div>
        )}

        {/* Real Step Provenance if completed */}
        {queryResponse?.status === "COMPLETED" && (
          <div className="border border-line rounded-lg p-2.5 bg-surface/70 space-y-1.5 text-[10px] text-muted">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald shrink-0" />
              <span>{t("workspace.schemaVerified")}</span>
              <span className="ml-auto font-mono text-faint">✓</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald shrink-0" />
              <span>{t("workspace.astCheckPassed")}</span>
              <span className="ml-auto font-mono text-faint">✓</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald shrink-0" />
              <span>{t("workspace.engineCompleted")}</span>
              <span className="ml-auto font-mono text-faint">
                {formatDuration(queryResponse.execution_time_ms)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
