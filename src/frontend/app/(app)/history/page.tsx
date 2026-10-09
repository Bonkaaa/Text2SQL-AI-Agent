"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  RotateCw,
  Copy,
  Check,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Plus,
} from "lucide-react";
import Link from "next/link";
import { useQueryHistory } from "@/hooks/useQueryHistory";
import { HistoryItem } from "@/lib/storage";
import { useLanguage } from "@/context/LanguageContext";

type StatusFilter = "ALL" | "SUCCESS" | "BLOCKED" | "ERROR";

export default function HistoryPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const { historyItems } = useQueryHistory();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [search, setSearch] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const statusTabs: { id: StatusFilter; label: string; count: number }[] = [
    { id: "ALL", label: t("history.allRuns"), count: historyItems.length },
    {
      id: "SUCCESS",
      label: t("history.statusSuccess"),
      count: historyItems.filter((h) => h.status === "SUCCESS").length,
    },
    {
      id: "BLOCKED",
      label: t("history.blocked"),
      count: historyItems.filter((h) => h.status === "BLOCKED").length,
    },
    {
      id: "ERROR",
      label: t("history.errors"),
      count: historyItems.filter((h) => h.status === "ERROR").length,
    },
  ];

  const filteredHistory = useMemo(() => {
    return historyItems.filter((item) => {
      const matchStatus =
        statusFilter === "ALL" || item.status === statusFilter;
      if (!matchStatus) return false;

      if (!search.trim()) return true;
      const term = search.toLowerCase();
      return (
        item.question.toLowerCase().includes(term) ||
        (item.sql && item.sql.toLowerCase().includes(term))
      );
    });
  }, [historyItems, statusFilter, search]);

  const handleRerun = (item: HistoryItem) => {
    router.push(`/workspace?q=${encodeURIComponent(item.question)}`);
  };

  const handleCopySQL = async (item: HistoryItem) => {
    if (!item.sql) return;
    try {
      await navigator.clipboard.writeText(item.sql);
      setCopiedId(item.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Heading & Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <div className="text-primary text-[10px] font-extrabold uppercase tracking-widest mb-1.5">
            {t("history.eyebrow")}
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            {t("history.title")}
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1 max-w-2xl leading-relaxed">
            {t("history.description")}
          </p>
        </div>

        <Link
          href="/workspace"
          className="inline-flex items-center gap-2 bg-primary hover:bg-primary-strong text-white px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>{t("history.newQuery")}</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Status Filter Tabs */}
        <div
          role="tablist"
          aria-label="History Statuses"
          className="flex items-center gap-1 bg-surface-2 p-1 rounded-xl border border-line overflow-x-auto"
        >
          {statusTabs.map((tab) => {
            const isActive = statusFilter === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={isActive}
                type="button"
                onClick={() => setStatusFilter(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                  isActive
                    ? "bg-surface text-primary shadow-xs font-bold"
                    : "text-muted hover:text-foreground hover:bg-surface/50"
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`text-[10px] font-mono tabular-nums px-1.5 py-0.2 rounded-full ${
                    isActive
                      ? "bg-primary-soft text-primary font-bold"
                      : "bg-surface text-muted"
                  }`}
                >
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div className="flex items-center gap-2 border border-line rounded-lg px-2.5 h-9 bg-surface text-xs text-muted w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-muted shrink-0" />
          <input
            type="text"
            placeholder={t("history.searchPlaceholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent border-0 outline-none text-xs text-foreground placeholder:text-muted"
          />
        </div>
      </div>

      {/* History Table */}
      <div className="bg-surface border border-line rounded-xl shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead className="bg-surface-2 text-muted text-[10px] font-bold uppercase border-b border-line">
              <tr>
                <th className="p-3">{t("history.colQuestion")}</th>
                <th className="p-3">{t("history.colStatus")}</th>
                <th className="p-3 text-right">{t("history.colRows")}</th>
                <th className="p-3 text-right">{t("history.colTime")}</th>
                <th className="p-3">{t("history.colTimestamp")}</th>
                <th className="p-3 text-right">{t("history.colActions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-xs text-muted">
                    {t("history.empty")}
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-2/60 transition">
                    <td className="p-3 max-w-sm">
                      <strong className="text-foreground block text-xs truncate">
                        {item.question}
                      </strong>
                      {item.sql && (
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <code className="text-muted text-[10px] font-mono truncate max-w-xs block">
                            {item.sql}
                          </code>
                          <button
                            type="button"
                            onClick={() => handleCopySQL(item)}
                            title={t("workspace.copySql")}
                            className="p-1 rounded text-muted hover:text-foreground shrink-0"
                          >
                            {copiedId === item.id ? (
                              <Check className="w-3 h-3 text-emerald" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      )}
                    </td>

                    <td className="p-3">
                      {item.status === "SUCCESS" && (
                        <span className="text-[10px] bg-emerald-soft text-emerald font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 border border-emerald/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald" />
                          SUCCESS
                        </span>
                      )}
                      {item.status === "BLOCKED" && (
                        <span className="text-[10px] bg-rose-soft text-rose font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 border border-rose/20">
                          <ShieldAlert className="w-3 h-3" />
                          BLOCKED
                        </span>
                      )}
                      {item.status === "ERROR" && (
                        <span className="text-[10px] bg-rose-soft text-rose font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 border border-rose/20">
                          <AlertTriangle className="w-3 h-3" />
                          ERROR
                        </span>
                      )}
                      {item.status === "PENDING" && (
                        <span className="text-[10px] bg-amber-soft text-amber font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 border border-amber/20">
                          <Clock className="w-3 h-3" />
                          PENDING
                        </span>
                      )}
                    </td>

                    <td className="p-3 text-right font-mono tabular-nums text-muted">
                      {item.rowCount !== undefined ? `${item.rowCount}` : "—"}
                    </td>

                    <td className="p-3 text-right font-mono tabular-nums text-muted">
                      {item.executionTimeMs !== undefined
                        ? `${item.executionTimeMs}ms`
                        : "—"}
                    </td>

                    <td className="p-3 text-muted text-[11px] font-mono">
                      {item.timestamp}
                    </td>

                    <td className="p-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleRerun(item)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 text-primary font-bold text-xs transition shadow-xs"
                      >
                        <RotateCw className="w-3 h-3 text-primary" />
                        <span>{t("history.rerun")}</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
