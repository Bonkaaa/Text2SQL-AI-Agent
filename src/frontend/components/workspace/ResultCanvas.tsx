"use client";

import {
  Sparkles,
  Table as TableIcon,
  BarChart3,
  Code2,
  Layers,
  Database,
  Loader2,
  Bookmark,
  BookmarkCheck,
} from "lucide-react";
import { QueryResponse } from "@/types/api";
import { useSavedQueries } from "@/hooks/useSavedQueries";
import { AnswerView } from "./views/AnswerView";
import { DataTableView } from "./views/DataTableView";
import { ChartView } from "./views/ChartView";
import { SQLViewer } from "./views/SQLViewer";
import { TraceView } from "./views/TraceView";

export type TabType = "answer" | "table" | "chart" | "sql" | "trace";

interface ResultCanvasProps {
  response?: QueryResponse | null;
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  isLoading?: boolean;
}

export function ResultCanvas({
  response,
  activeTab,
  onTabChange,
  isLoading = false,
}: ResultCanvasProps) {
  const { isSaved, saveQuery } = useSavedQueries();
  const isBookmarked = response?.question ? isSaved(response.question) : false;

  const handleToggleBookmark = () => {
    if (!response?.question) return;
    saveQuery({
      title: response.question,
      question: response.question,
      sql: response.sql,
      tag: "Analytics",
    });
  };

  const tabs: { id: TabType; label: string; icon: React.ReactNode; badge?: number }[] = [
    {
      id: "answer",
      label: "Answer",
      icon: <Sparkles className="w-3.5 h-3.5" />,
    },
    {
      id: "table",
      label: "Table",
      icon: <TableIcon className="w-3.5 h-3.5" />,
      badge: response?.data?.length,
    },
    {
      id: "chart",
      label: "Chart",
      icon: <BarChart3 className="w-3.5 h-3.5" />,
    },
    {
      id: "sql",
      label: "SQL",
      icon: <Code2 className="w-3.5 h-3.5" />,
    },
    {
      id: "trace",
      label: "Trace",
      icon: <Layers className="w-3.5 h-3.5" />,
      badge: response?.tasks?.length,
    },
  ];

  // Loading State
  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-surface rounded-2xl border border-line h-full min-h-[460px] text-center space-y-3">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
        <div className="space-y-1">
          <h4 className="text-sm font-bold text-foreground">Executing Query & Synthesizing Results</h4>
          <p className="text-xs text-muted max-w-sm">
            Retrieving TPC-DS schema, validating AST syntax with sqlglot, and executing DuckDB analytics...
          </p>
        </div>
      </div>
    );
  }

  // Empty State (No query executed yet)
  if (!response) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-surface rounded-2xl border border-line h-full min-h-[460px] text-center space-y-3">
        <div className="p-3 rounded-2xl bg-surface-2 border border-line text-muted">
          <Database className="w-8 h-8 text-primary" />
        </div>
        <div className="space-y-1 max-w-sm">
          <h4 className="text-sm font-bold text-foreground">Ready for Analytics Exploration</h4>
          <p className="text-xs text-muted leading-relaxed">
            Enter a natural language question on the left to generate SQL, view tabular results, and explore interactive Recharts visualizations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-surface rounded-2xl border border-line shadow-card overflow-hidden">
      {/* Tab Navigation Bar with Save Query Bookmark Action */}
      <div className="flex items-center justify-between border-b border-line bg-surface-2/40 px-3 py-1.5 overflow-x-auto gap-2">
        <div
          role="tablist"
          aria-label="Result Views"
          className="flex items-center gap-1"
        >
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={isActive}
                aria-controls={`panel-${tab.id}`}
                type="button"
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? "bg-surface text-primary shadow-xs border border-line"
                    : "text-muted hover:text-foreground hover:bg-surface-2/60"
                }`}
              >
                <span className={isActive ? "text-primary" : "text-muted"}>
                  {tab.icon}
                </span>
                <span>{tab.label}</span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span
                    className={`text-[10px] font-mono tabular-nums px-1.5 py-0.2 rounded-full font-bold ${
                      isActive
                        ? "bg-primary-soft text-primary"
                        : "bg-surface-2 text-muted"
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Save Query Bookmark Button */}
        {response?.question && (
          <button
            type="button"
            onClick={handleToggleBookmark}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition border shrink-0 ${
              isBookmarked
                ? "bg-primary-soft text-primary border-primary/20 font-bold"
                : "bg-surface hover:bg-surface-2 text-muted hover:text-foreground border-line"
            }`}
          >
            {isBookmarked ? (
              <>
                <BookmarkCheck className="w-3.5 h-3.5 text-primary" />
                <span>Saved</span>
              </>
            ) : (
              <>
                <Bookmark className="w-3.5 h-3.5 text-muted" />
                <span>Save query</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Tab Content Panel */}
      <div
        role="tabpanel"
        id={`panel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className="p-4 flex-1 overflow-y-auto"
      >
        {activeTab === "answer" && (
          <AnswerView
            response={response}
            onJumpToTable={() => onTabChange("table")}
          />
        )}

        {activeTab === "table" && (
          <DataTableView
            data={response.data || []}
            columns={response.columns || []}
            totalRowCount={response.data?.length}
          />
        )}

        {activeTab === "chart" && <ChartView response={response} />}

        {activeTab === "sql" && <SQLViewer sql={response.sql || ""} />}

        {activeTab === "trace" && <TraceView response={response} />}
      </div>
    </div>
  );
}
