"use client";

import React from "react";
import { Sparkles, CheckCircle2 } from "lucide-react";

interface ExecutiveSummaryCardProps {
  directAnswer?: string | null;
  detailedInsight?: string[] | null;
}

export const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({
  directAnswer,
  detailedInsight,
}) => {
  const hasDirect = Boolean(directAnswer && directAnswer.trim().length > 0);
  const hasInsights = Boolean(detailedInsight && detailedInsight.length > 0);

  if (!hasDirect && !hasInsights) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3 p-4 rounded-xl bg-surface-secondary/50 border border-border-default/70 backdrop-blur-sm shadow-sm my-3">
      {/* Direct Answer Headline */}
      {hasDirect && (
        <div className="flex items-start gap-2.5">
          <div className="p-1 rounded-md bg-primary-500/10 text-primary-400 mt-0.5 shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Tóm tắt phân tích điều hành
            </h4>
            <p className="text-sm font-medium text-slate-100 leading-relaxed">
              {directAnswer}
            </p>
          </div>
        </div>
      )}

      {/* Key Insights List */}
      {hasInsights && detailedInsight && (
        <div className={`flex flex-col gap-2 ${hasDirect ? "pt-2 border-t border-border-default/40" : ""}`}>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Phát hiện định lượng quan trọng
          </div>
          <ul className="flex flex-col gap-1.5 text-xs text-slate-300">
            {detailedInsight.map((insight, idx) => (
              <li key={idx} className="flex items-start gap-2 leading-relaxed">
                <CheckCircle2 className="w-3.5 h-3.5 text-primary-400 mt-0.5 shrink-0" />
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
