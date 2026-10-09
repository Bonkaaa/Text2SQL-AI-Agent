"use client";

import React from "react";
import { Database, CheckCircle2, Layers, Cpu, Clock } from "lucide-react";

interface DataSourceCardProps {
  tableCount?: number;
  status?: "connected" | "disconnected" | "syncing";
}

export function DataSourceCard({
  tableCount = 24,
  status = "connected",
}: DataSourceCardProps) {
  return (
    <div className="bg-surface border border-line rounded-xl p-4 shadow-card space-y-3">
      {/* Top row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary-soft text-primary grid place-items-center">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">
                DuckDB TPC-DS Benchmark
              </h3>
              <span className="text-[10px] font-bold text-emerald bg-emerald-soft px-2 py-0.5 rounded-full inline-flex items-center gap-1 border border-emerald/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald animate-pulse" />
                Connected
              </span>
            </div>
            <p className="text-[11px] text-muted">
              Enterprise Omnichannel Retail Warehouse · DuckDB In-Memory OLAP
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted">
          <span className="inline-flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-muted" />
            <span>Metadata auto-synced</span>
          </span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-line/60">
        <div className="p-2 rounded-lg bg-surface-2 border border-line">
          <span className="text-[10px] text-muted font-semibold block">Total Tables</span>
          <strong className="text-base font-extrabold text-foreground font-mono tabular-nums">
            {tableCount}
          </strong>
        </div>
        <div className="p-2 rounded-lg bg-surface-2 border border-line">
          <span className="text-[10px] text-muted font-semibold block">Sales Channels</span>
          <strong className="text-base font-extrabold text-foreground font-mono">
            Store, Web, Catalog
          </strong>
        </div>
        <div className="p-2 rounded-lg bg-surface-2 border border-line">
          <span className="text-[10px] text-muted font-semibold block">SQL Engine</span>
          <strong className="text-base font-extrabold text-foreground font-mono">
            DuckDB SQL
          </strong>
        </div>
        <div className="p-2 rounded-lg bg-surface-2 border border-line">
          <span className="text-[10px] text-muted font-semibold block">Modeled Records</span>
          <strong className="text-base font-extrabold text-foreground font-mono tabular-nums">
            ~17.5M rows
          </strong>
        </div>
      </div>
    </div>
  );
}
