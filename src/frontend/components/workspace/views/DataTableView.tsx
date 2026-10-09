"use client";

import React, { useState, useMemo } from "react";
import {
  Download,
  Copy,
  Check,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { formatNumber } from "@/lib/formatters";
import { useLanguage } from "@/context/LanguageContext";

interface DataTableViewProps {
  data: Record<string, any>[];
  columns: string[];
  totalRowCount?: number;
}

type SortDirection = "asc" | "desc" | null;

export function DataTableView({
  data = [],
  columns = [],
  totalRowCount,
}: DataTableViewProps) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  const handleSort = (column: string) => {
    if (sortColumn !== column) {
      setSortColumn(column);
      setSortDirection("asc");
    } else if (sortDirection === "asc") {
      setSortDirection("desc");
    } else {
      setSortColumn(null);
      setSortDirection(null);
    }
    setCurrentPage(1);
  };

  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return data;
    const term = searchTerm.toLowerCase();
    return data.filter((row) =>
      columns.some((col) => {
        const val = row[col];
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(term);
      })
    );
  }, [data, columns, searchTerm]);

  const sortedData = useMemo(() => {
    if (!sortColumn || !sortDirection) return filteredData;

    return [...filteredData].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortDirection === "asc"
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
  }, [filteredData, sortColumn, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize));
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  const exportCSV = () => {
    if (!data.length || !columns.length) return;

    const headerRow = columns.map((col) => `"${col.replace(/"/g, '""')}"`).join(",");
    const rows = sortedData.map((row) =>
      columns
        .map((col) => {
          const val = row[col];
          if (val === null || val === undefined) return '""';
          return `"${String(val).replace(/"/g, '""')}"`;
        })
        .join(",")
    );

    const csvContent = [headerRow, ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `query_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = async () => {
    if (!data.length || !columns.length) return;
    const headerRow = columns.join("\t");
    const rows = sortedData.map((row) =>
      columns.map((col) => (row[col] === null || row[col] === undefined ? "" : String(row[col]))).join("\t")
    );
    const tsvContent = [headerRow, ...rows].join("\n");

    try {
      await navigator.clipboard.writeText(tsvContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const isNumericColumn = (col: string) => {
    return data.some((r) => typeof r[col] === "number");
  };

  if (!data || data.length === 0) {
    return (
      <div className="bg-surface border border-line rounded-xl p-8 text-center text-muted text-xs">
        {t("workspace.noData")}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Table Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 text-xs text-muted">
          <span className="font-semibold text-foreground">
            {totalRowCount || data.length} {t("common.rows")}
          </span>
          {searchTerm && <span>({sortedData.length} {t("common.rows")})</span>}
          <span>•</span>
          <span>{columns.length} {t("sources.cols")}</span>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          {/* Quick search */}
          <div className="relative flex-1 sm:w-48">
            <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder={t("workspace.filterRowsPlaceholder")}
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-line bg-surface text-foreground placeholder:text-muted focus:outline-none focus:border-primary"
            />
          </div>

          {/* Copy Table */}
          <button
            type="button"
            onClick={copyToClipboard}
            className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 text-foreground transition-colors"
            title={t("workspace.copyTable")}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald" />
                <span className="text-emerald">{t("workspace.copied")}</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-muted" />
                <span>{t("common.copy")}</span>
              </>
            )}
          </button>

          {/* Export CSV */}
          <button
            type="button"
            onClick={exportCSV}
            className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 text-foreground transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-primary" />
            <span>{t("workspace.exportCsv")}</span>
          </button>
        </div>
      </div>

      {/* Table Canvas with Sticky Header */}
      <div className="border border-line rounded-xl bg-surface overflow-hidden shadow-card">
        <div className="overflow-x-auto max-h-[520px]">
          <table className="w-full text-xs border-collapse">
            <thead className="bg-surface-2 border-b border-line sticky top-0 z-10">
              <tr>
                <th className="w-10 px-3 py-2 text-[10px] font-bold text-muted text-center border-r border-line/60">
                  #
                </th>
                {columns.map((col) => {
                  const isNum = isNumericColumn(col);
                  const isSorted = sortColumn === col;

                  return (
                    <th
                      key={col}
                      onClick={() => handleSort(col)}
                      className={`px-3 py-2 font-bold text-foreground cursor-pointer select-none hover:bg-surface-3 transition-colors ${
                        isNum ? "text-right" : "text-left"
                      }`}
                    >
                      <div
                        className={`inline-flex items-center gap-1 ${
                          isNum ? "justify-end" : "justify-start"
                        }`}
                      >
                        <span>{col}</span>
                        {isSorted ? (
                          sortDirection === "asc" ? (
                            <ChevronUp className="w-3 h-3 text-primary" />
                          ) : (
                            <ChevronDown className="w-3 h-3 text-primary" />
                          )
                        ) : (
                          <ChevronsUpDown className="w-3 h-3 text-muted/60 opacity-0 group-hover:opacity-100" />
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-line/70">
              {paginatedData.map((row, rowIdx) => {
                const actualIndex = (currentPage - 1) * pageSize + rowIdx + 1;
                return (
                  <tr
                    key={rowIdx}
                    className="hover:bg-primary-soft/20 transition-colors"
                  >
                    <td className="px-3 py-2 text-[10px] text-muted text-center font-mono tabular-nums border-r border-line/60 bg-surface-2/40">
                      {actualIndex}
                    </td>
                    {columns.map((col) => {
                      const val = row[col];
                      const isNum = typeof val === "number";

                      return (
                        <td
                          key={col}
                          className={`px-3 py-2 text-foreground ${
                            isNum
                              ? "text-right font-mono tabular-nums"
                              : "text-left"
                          }`}
                        >
                          {val === null || val === undefined ? (
                            <span className="text-muted/60 italic">-</span>
                          ) : isNum ? (
                            formatNumber(val)
                          ) : (
                            String(val)
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-3 py-2 border-t border-line bg-surface-2/60 text-xs text-muted">
            <span>
              {t("workspace.pageOf")} {currentPage} {t("workspace.of")} {totalPages}
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="p-1 rounded hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="p-1 rounded hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
