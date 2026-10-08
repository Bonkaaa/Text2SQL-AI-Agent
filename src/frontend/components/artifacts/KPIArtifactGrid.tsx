"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { KpiArtifact } from "../../types/artifacts";

interface KPIArtifactGridProps {
  kpis: KpiArtifact[];
}

function formatKpiValue(val: number | string): string {
  if (typeof val === "number") {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(val);
  }
  return String(val);
}

export const KPIArtifactGrid: React.FC<KPIArtifactGridProps> = ({ kpis }) => {
  if (!kpis || kpis.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 my-3">
      {kpis.map((kpi, idx) => {
        const isIncrease =
          kpi.delta_type === "increase" ||
          (!kpi.delta_type && typeof kpi.delta === "number" && kpi.delta > 0);
        const isDecrease =
          kpi.delta_type === "decrease" ||
          (!kpi.delta_type && typeof kpi.delta === "number" && kpi.delta < 0);

        let deltaSign = "";
        if (typeof kpi.delta === "number" && kpi.delta > 0) {
          deltaSign = "+";
        }

        return (
          <div
            key={idx}
            className="flex flex-col justify-between p-4 rounded-xl bg-surface-secondary/70 border border-border-default/80 hover:border-border-hover/80 transition-colors shadow-sm"
          >
            {/* Header: Label & Delta Badge */}
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider truncate">
                {kpi.title}
              </span>

              {kpi.delta != null && (
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium font-mono-data border ${
                    isIncrease
                      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                      : isDecrease
                      ? "text-rose-400 bg-rose-500/10 border-rose-500/20"
                      : "text-slate-400 bg-slate-800 border-slate-700/60"
                  }`}
                >
                  {isIncrease ? (
                    <TrendingUp className="w-3 h-3 text-emerald-400" />
                  ) : isDecrease ? (
                    <TrendingDown className="w-3 h-3 text-rose-400" />
                  ) : (
                    <Minus className="w-3 h-3 text-slate-400" />
                  )}
                  {deltaSign}
                  {kpi.delta}%
                </span>
              )}
            </div>

            {/* Value & Unit */}
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-bold text-white font-mono-data tracking-tight">
                {formatKpiValue(kpi.value)}
              </span>
              {kpi.unit && (
                <span className="text-xs font-medium text-slate-400">
                  {kpi.unit}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
