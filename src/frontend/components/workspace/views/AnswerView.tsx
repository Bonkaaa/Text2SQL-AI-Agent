"use client";

import React from "react";
import { Sparkles, TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import { QueryResponse, KpiArtifact } from "@/types/api";
import { formatCurrency, formatNumber } from "@/lib/formatters";

interface AnswerViewProps {
  response: QueryResponse;
  onJumpToTable: () => void;
}

export function AnswerView({ response, onJumpToTable }: AnswerViewProps) {
  const directAnswer =
    response.final_answer ||
    response.response_package?.direct_answer ||
    "Phân tích dữ liệu đã hoàn tất.";

  const insights = response.response_package?.detailed_insight || [];
  const kpiArtifacts = (response.response_package?.artifacts?.filter(
    (a) => a.type === "kpi"
  ) || []) as KpiArtifact[];

  return (
    <div className="space-y-4">
      {/* Executive Summary Callout */}
      <div className="bg-surface-2 border border-line rounded-xl p-4 shadow-sm space-y-2">
        <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
          <Sparkles className="w-4 h-4 text-primary" />
          <span>Executive Summary</span>
        </div>
        <p className="text-xs text-foreground leading-relaxed m-0">{directAnswer}</p>
      </div>

      {/* KPI Cards Grid */}
      {kpiArtifacts.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {kpiArtifacts.map((kpi, idx) => (
            <div key={idx} className="bg-surface border border-line rounded-xl p-3.5 shadow-card">
              <span className="text-[10px] text-muted font-semibold block">{kpi.title}</span>
              <div className="flex items-baseline gap-2 mt-1">
                <strong className="text-xl font-extrabold text-foreground font-mono tabular-nums">
                  {kpi.unit === "USD" ? formatCurrency(kpi.value) : formatNumber(kpi.value)}
                </strong>
                {kpi.delta !== undefined && (
                  <span
                    className={`text-[10px] font-bold inline-flex items-center gap-0.5 ${
                      kpi.delta_type === "decrease" ? "text-rose" : "text-emerald"
                    }`}
                  >
                    {kpi.delta_type === "decrease" ? (
                      <TrendingDown className="w-3 h-3" />
                    ) : (
                      <TrendingUp className="w-3 h-3" />
                    )}
                    {kpi.delta > 0 ? `+${kpi.delta}%` : `${kpi.delta}%`}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Key Takeaways & Insights */}
      {insights.length > 0 && (
        <div className="bg-primary-soft/40 border border-primary/20 rounded-xl p-4 space-y-2">
          <strong className="text-xs font-bold text-primary block">
            Business Insights & Findings
          </strong>
          <ul className="text-xs text-foreground space-y-1.5 pl-4 list-disc leading-relaxed">
            {insights.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Table Jump Action */}
      <div className="pt-2">
        <button
          type="button"
          onClick={onJumpToTable}
          className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline"
        >
          Inspect underlying rows in table view <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
