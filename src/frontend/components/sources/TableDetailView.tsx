"use client";

import React from "react";
import {
  Sparkles,
  Key,
  Link as LinkIcon,
  Table as TableIcon,
  ArrowRight,
} from "lucide-react";
import { TableMetadata } from "@/types/schema";
import { formatNumber } from "@/lib/formatters";
import { useLanguage } from "@/context/LanguageContext";

interface TableDetailViewProps {
  table: TableMetadata;
  onAskQuestion: (question: string) => void;
  onClose?: () => void;
}

export function TableDetailView({
  table,
  onAskQuestion,
}: TableDetailViewProps) {
  const { t } = useLanguage();
  const primaryQuestion =
    table.sampleQuestions[0] || `Phân tích dữ liệu trong bảng ${table.name}`;

  return (
    <div className="bg-surface border border-line rounded-xl p-4 md:p-5 shadow-card space-y-4">
      {/* Table Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-line pb-3.5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-primary-soft text-primary">
              <TableIcon className="w-4 h-4" />
            </span>
            <h2 className="text-base font-extrabold text-foreground font-mono">
              {table.name}
            </h2>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-surface-2 text-muted border border-line">
              {table.categoryLabel}
            </span>
          </div>
          <div className="text-xs font-semibold text-muted mt-1">
            {table.displayName} •{" "}
            <span className="font-mono tabular-nums">
              ~{formatNumber(table.rowCountEstimate)} {t("common.rows")}
            </span>
          </div>
          <p className="text-xs text-foreground mt-2 leading-relaxed max-w-2xl">
            {table.description}
          </p>
        </div>

        {/* Primary Action Button */}
        <button
          type="button"
          onClick={() => onAskQuestion(primaryQuestion)}
          aria-label="Hỏi về bảng này"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-primary hover:bg-primary-strong text-white text-xs font-bold transition shadow-sm shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>{t("sources.askAboutTable")}</span>
        </button>
      </div>

      {/* Suggested Analysis Prompts */}
      {table.sampleQuestions.length > 0 && (
        <div className="p-3 rounded-lg bg-surface-2 border border-line space-y-2">
          <div className="flex items-center gap-1 text-[11px] font-bold text-muted">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            <span>{t("sources.suggestedPrompts")}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {table.sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onAskQuestion(q)}
                className="text-left text-xs bg-surface hover:bg-primary-soft/40 border border-line hover:border-primary/40 px-2.5 py-1.5 rounded-md text-foreground transition flex items-center gap-1.5 group"
              >
                <span>{q}</span>
                <ArrowRight className="w-3 h-3 text-muted group-hover:text-primary transition-transform group-hover:translate-x-0.5" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Columns Schema Table */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <strong className="text-xs font-bold text-foreground">
            {t("sources.columnsAndTypes")} ({table.columns.length} {t("sources.cols")})
          </strong>
        </div>

        <div className="border border-line rounded-lg overflow-x-auto bg-surface">
          <table className="w-full text-xs text-left">
            <thead className="bg-surface-2 border-b border-line text-[10px] text-muted font-bold uppercase">
              <tr>
                <th className="px-3 py-2">{t("sources.columnName")}</th>
                <th className="px-3 py-2">{t("sources.type")}</th>
                <th className="px-3 py-2">{t("sources.constraints")}</th>
                <th className="px-3 py-2">{t("sources.descriptionCol")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/70">
              {table.columns.map((col) => (
                <tr key={col.name} className="hover:bg-surface-2/40 transition-colors">
                  <td className="px-3 py-2 font-mono font-bold text-foreground whitespace-nowrap">
                    {col.name}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-muted whitespace-nowrap">
                    {col.type}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      {col.isPrimaryKey && (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-amber-soft text-amber border border-amber/30">
                          <Key className="w-2.5 h-2.5" />
                          PK
                        </span>
                      )}
                      {col.isForeignKey && (
                        <span
                          className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary-soft text-primary border border-primary/20"
                          title={col.references ? `References ${col.references}` : undefined}
                        >
                          <LinkIcon className="w-2.5 h-2.5" />
                          FK
                        </span>
                      )}
                      {!col.isPrimaryKey && !col.isForeignKey && (
                        <span className="text-[10px] text-muted/60">
                          {col.nullable ? "Nullable" : "Not Null"}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-foreground text-xs leading-snug">
                    <span>{col.description}</span>
                    {col.references && (
                      <span className="text-[10px] text-muted block font-mono">
                        → {col.references}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
