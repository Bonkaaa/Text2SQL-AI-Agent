"use client";

import React from "react";
import { Database, ChevronDown } from "lucide-react";

interface DatabaseSwitcherProps {
  databaseName?: string;
  engineInfo?: string;
  status?: "connected" | "disconnected" | "syncing";
}

export function DatabaseSwitcher({
  databaseName = "AdventureWorks",
  engineInfo = "DuckDB TPC-DS (24 tables)",
  status = "connected",
}: DatabaseSwitcherProps) {
  return (
    <button
      type="button"
      className="w-[calc(100%-8px)] mx-1 mb-5 p-2.5 rounded-xl border border-line bg-surface-2 text-foreground flex items-center gap-2.5 text-left transition-colors hover:border-line-strong hover:bg-surface-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary max-w-full"
      aria-label="Current database selection"
    >
      <div className="w-[30px] h-[30px] rounded-lg border border-line bg-surface text-primary flex items-center justify-center shrink-0 shadow-sm">
        <Database className="w-4 h-4" />
      </div>

      <div className="min-w-0 flex-1 hidden md:block">
        <strong className="block text-[11px] font-bold truncate leading-tight">
          {databaseName}
        </strong>
        <div className="flex items-center gap-1.5 text-[10px] text-muted mt-0.5 truncate">
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
              status === "connected"
                ? "bg-[var(--green)]"
                : status === "syncing"
                ? "bg-[var(--amber)]"
                : "bg-[var(--red)]"
            }`}
          />
          <span className="truncate">{engineInfo}</span>
        </div>
      </div>

      <ChevronDown className="w-3.5 h-3.5 text-muted shrink-0 hidden md:block ml-auto" />
    </button>
  );
}
