"use client";

import React, { useState, useMemo } from "react";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  X,
  Download,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  SlidersHorizontal,
} from "lucide-react";
import { exportToCsv } from "@/services/exportCsv";
import { copyMarkdownToClipboard } from "@/utils/tableExport";
import { useOptionalAppContext } from "@/context/AppContext";
import type { TableArtifact } from "@/types/artifacts";

export interface DataTableProps {
  artifact?: TableArtifact;
  columns?: string[];
  data?: Record<string, any>[];
  initialPageSize?: number;
  tableName?: string;
  enableExport?: boolean;
  enableCopyMarkdown?: boolean;
  enableSearch?: boolean;
  className?: string;
}

export function DataTable({
  artifact,
  columns: propColumns,
  data: propData,
  initialPageSize = 5,
  tableName = "query_result",
  enableExport = true,
  enableCopyMarkdown = true,
  enableSearch = true,
  className = "",
}: DataTableProps) {
  const appContext = useOptionalAppContext();

  // Chuẩn hóa props giữa TableArtifact và props độc lập
  const columns = useMemo(() => {
    if (artifact?.columns && artifact.columns.length > 0) {
      return artifact.columns;
    }
    if (propColumns && propColumns.length > 0) {
      return propColumns;
    }
    if (propData && propData.length > 0) {
      return Object.keys(propData[0]);
    }
    return [];
  }, [artifact, propColumns, propData]);

  const rawData = useMemo(() => {
    if (artifact?.rows) {
      return artifact.rows;
    }
    if (propData) {
      return propData;
    }
    return [];
  }, [artifact, propData]);

  const title = artifact?.title || tableName;

  // Trạng thái tìm kiếm, sắp xếp, phân trang và mật độ hiển thị
  const [searchTerm, setSearchTerm] = useState("");
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc" | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");
  const [copied, setCopied] = useState(false);

  // Nhận biết cột số để căn phải và định dạng font-mono-data
  const numericColumns = useMemo(() => {
    const set = new Set<string>();
    if (!columns || columns.length === 0 || !rawData || rawData.length === 0) {
      return set;
    }
    columns.forEach((col) => {
      // Nếu có metadata format từ backend
      if (
        artifact?.column_formats &&
        (artifact.column_formats[col] === "currency" ||
          artifact.column_formats[col] === "integer" ||
          artifact.column_formats[col] === "percentage" ||
          artifact.column_formats[col] === "number")
      ) {
        set.add(col);
        return;
      }
      // Kiểm tra mẫu 5 dòng đầu
      const sample = rawData.slice(0, 5);
      const isNum = sample.some(
        (r) => typeof r[col] === "number" && !isNaN(r[col])
      );
      if (isNum) {
        set.add(col);
      }
    });
    return set;
  }, [columns, rawData, artifact]);

  // 1. Lọc dữ liệu theo từ khóa tìm kiếm (Client-side Search)
  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return rawData;
    const term = searchTerm.toLowerCase().trim();

    return rawData.filter((row) =>
      columns.some((col) => {
        const val = row[col];
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(term);
      })
    );
  }, [rawData, columns, searchTerm]);

  // 2. Sắp xếp dữ liệu (Column Sorting)
  const sortedData = useMemo(() => {
    if (!sortColumn || !sortDirection) return filteredData;

    return [...filteredData].sort((a, b) => {
      const valA = a[sortColumn];
      const valB = b[sortColumn];

      if (valA === valB) return 0;
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      // So sánh số học nếu cả 2 là số
      if (typeof valA === "number" && typeof valB === "number") {
        return sortDirection === "asc" ? valA - valB : valB - valA;
      }

      // So sánh chuỗi
      const strA = String(valA).toLowerCase();
      const strB = String(valB).toLowerCase();
      return sortDirection === "asc"
        ? strA.localeCompare(strB)
        : strB.localeCompare(strA);
    });
  }, [filteredData, sortColumn, sortDirection]);

  // Xử lý đổi hướng sắp xếp khi click header
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
  };

  // 3. Phân trang dữ liệu
  const totalRows = sortedData.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalRows);
  const paginatedRows = sortedData.slice(startIndex, endIndex);

  // Xử lý thay đổi tìm kiếm -> reset về trang 1
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setPage(1);
  };

  // 4. Xuất file CSV
  const handleExportCsv = () => {
    const filename = `${title.toLowerCase().replace(/[^a-z0-9]/gi, "_")}_${new Date().getTime()}`;
    exportToCsv(filename, columns, sortedData.length > 0 ? sortedData : rawData);
    appContext?.showToast("Đã tải xuống tệp dữ liệu CSV", "success", 2000);
  };

  // 5. Sao chép bảng Markdown vào Clipboard
  const handleCopyMarkdown = async () => {
    const success = await copyMarkdownToClipboard(
      columns,
      sortedData.length > 0 ? sortedData : rawData
    );
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      appContext?.showToast("Đã sao chép bảng Markdown vào bộ nhớ tạm", "success", 2000);
    }
  };

  const cellPadding = density === "comfortable" ? "py-2.5 px-3" : "py-1.5 px-2.5 text-[11px]";

  return (
    <div
      className={`space-y-3 rounded-2xl border border-border-default/80 bg-surface-secondary/70 p-4 sm:p-5 backdrop-blur-md transition-all shadow-sm ${className}`}
      role="region"
      aria-label="Bảng dữ liệu phân tích TPC-H"
    >
      {/* Top Toolbar: Title, Search & Action Buttons */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Title (nếu có) */}
        {title && title !== "query_result" && (
          <div className="flex items-center gap-2 mr-2">
            <span className="text-xs font-bold text-slate-200 tracking-wide uppercase">
              {title}
            </span>
          </div>
        )}

        {/* Left: Search Bar */}
        {enableSearch && (
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={handleSearchChange}
              placeholder="Tìm kiếm trong bảng..."
              className="w-full pl-8 pr-7 py-1.5 rounded-xl bg-surface-primary/80 border border-border-default/80 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary-500/50 transition-colors"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => {
                  setSearchTerm("");
                  setPage(1);
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                aria-label="Xóa tìm kiếm"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        {/* Right Actions: Density, Copy Markdown, Export CSV */}
        <div className="flex items-center gap-2">
          {/* Density Toggle Button */}
          <button
            type="button"
            onClick={() =>
              setDensity((d) => (d === "comfortable" ? "compact" : "comfortable"))
            }
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-surface-primary hover:bg-surface-primary/80 transition-all border border-border-default/80 active:scale-[0.98]"
            aria-label={`Mật độ ${density === "comfortable" ? "Comfortable" : "Compact"}`}
            title="Chuyển đổi mật độ hiển thị dòng"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden sm:inline">
              {density === "comfortable" ? "Rộng" : "Gọn"}
            </span>
          </button>

          {/* Copy Markdown Button */}
          {enableCopyMarkdown && (
            <button
              type="button"
              onClick={handleCopyMarkdown}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-surface-primary hover:bg-surface-primary/80 hover:text-white transition-all border border-border-default/80 active:scale-[0.98]"
              aria-label="Sao chép Markdown"
              title="Sao chép bảng dưới dạng Markdown"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-slate-400" />
              )}
              <span className="hidden sm:inline">Sao chép</span>
            </button>
          )}

          {/* Export CSV Button */}
          {enableExport && (
            <button
              type="button"
              onClick={handleExportCsv}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-surface-primary hover:bg-surface-primary/80 hover:text-white transition-all border border-border-default/80 active:scale-[0.98]"
              aria-label="Xuất CSV"
              title="Tải xuống tệp CSV chuẩn UTF-8"
            >
              <Download className="w-3.5 h-3.5 text-primary-400" />
              <span>Xuất CSV</span>
            </button>
          )}
        </div>
      </div>

      {/* Table Container with Sticky Header */}
      <div className="relative max-h-[460px] overflow-auto rounded-xl border border-border-default/80 custom-scrollbar bg-surface-primary/60">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="sticky top-0 bg-surface-secondary/95 backdrop-blur-md z-10 border-b border-border-default shadow-sm">
            <tr>
              {columns.map((col) => {
                const isSorted = sortColumn === col;
                const isNumeric = numericColumns.has(col);
                return (
                  <th
                    key={col}
                    className={`${cellPadding} font-semibold text-slate-300 whitespace-nowrap ${
                      isNumeric ? "text-right" : "text-left"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleSort(col)}
                      className={`inline-flex items-center gap-1.5 hover:text-primary-300 transition-colors focus:outline-none group ${
                        isNumeric ? "flex-row-reverse" : ""
                      }`}
                      aria-label={`Sắp xếp cột ${col}`}
                    >
                      <span>{col}</span>
                      {isSorted ? (
                        sortDirection === "asc" ? (
                          <ArrowUp className="w-3.5 h-3.5 text-primary-400 shrink-0" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-primary-400 shrink-0" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-500 opacity-60 group-hover:opacity-100 transition-opacity shrink-0" />
                      )}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-default/50">
            {paginatedRows.length > 0 ? (
              paginatedRows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="hover:bg-surface-secondary/40 transition-colors"
                >
                  {columns.map((col) => {
                    const value = row[col];
                    const isNumeric = numericColumns.has(col);
                    return (
                      <td
                        key={col}
                        className={`${cellPadding} text-slate-200 whitespace-nowrap ${
                          isNumeric
                            ? "text-right font-mono-data tabular-nums text-emerald-300/90"
                            : "text-left text-slate-300"
                        }`}
                      >
                        {value !== null && value !== undefined
                          ? typeof value === "number"
                            ? value.toLocaleString("en-US")
                            : String(value)
                          : "-"}
                      </td>
                    );
                  })}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={Math.max(1, columns.length)}
                  className="py-8 text-center text-slate-400 text-xs"
                >
                  <FileSpreadsheet className="w-6 h-6 text-slate-500 mx-auto mb-1.5" />
                  <span>Không tìm thấy dữ liệu phù hợp</span>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Bottom Pagination Bar */}
      <div className="flex items-center justify-between text-xs text-slate-400 pt-1 px-1 flex-wrap gap-2">
        <span>
          Hiển thị {totalRows === 0 ? 0 : startIndex + 1} - {endIndex} của{" "}
          {totalRows} dòng
        </span>

        <div className="flex items-center gap-3">
          {/* Page Size Selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-slate-500">Mỗi trang:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="bg-surface-primary border border-border-default/80 rounded-lg text-[11px] text-slate-300 px-2 py-0.5 focus:outline-none focus:border-primary-500/50"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-primary hover:bg-surface-primary/80 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition-colors border border-border-default/80"
              aria-label="Trang trước"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Trước</span>
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-primary hover:bg-surface-primary/80 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition-colors border border-border-default/80"
              aria-label="Trang sau"
            >
              <span>Sau</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DataTable;
