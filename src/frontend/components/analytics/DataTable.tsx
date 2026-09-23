"use client";

import React, { useState, useMemo } from "react";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  X,
  Download,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
} from "lucide-react";
import { exportToCsv } from "@/services/exportCsv";
import { useOptionalAppContext } from "@/context/AppContext";

export interface DataTableProps {
  columns: string[];
  data: Record<string, any>[];
  initialPageSize?: number;
  tableName?: string;
  enableExport?: boolean;
  enableSearch?: boolean;
  className?: string;
}

export function DataTable({
  columns,
  data,
  initialPageSize = 5,
  tableName = "query_result",
  enableExport = true,
  enableSearch = true,
  className = "",
}: DataTableProps) {
  const appContext = useOptionalAppContext();

  // Trạng thái tìm kiếm, sắp xếp và phân trang
  const [searchTerm, setSearchTerm] = useState("");
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc" | null>(
    null
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  // 1. Lọc dữ liệu theo từ khóa tìm kiếm (Client-side Search)
  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return data;
    const term = searchTerm.toLowerCase().trim();

    return data.filter((row) =>
      columns.some((col) => {
        const val = row[col];
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(term);
      })
    );
  }, [data, columns, searchTerm]);

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
    const filename = `${tableName}_${new Date().getTime()}`;
    exportToCsv(filename, columns, sortedData.length > 0 ? sortedData : data);
    appContext?.showToast("Đã tải xuống tệp dữ liệu CSV", "success", 2000);
  };

  return (
    <div
      className={`space-y-3 rounded-2xl border border-surface-border bg-[#0a0f1d]/80 p-4 sm:p-5 backdrop-blur-md transition-all shadow-card ${className}`}
      role="region"
      aria-label="Bảng dữ liệu phân tích TPC-H"
    >
      {/* Top Toolbar: Search & Export CSV */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Search Bar */}
        {enableSearch && (
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={handleSearchChange}
              placeholder="Tìm kiếm trong bảng..."
              className="w-full pl-8 pr-7 py-1.5 rounded-xl bg-surface-subtle/80 border border-surface-border text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500/50 transition-colors"
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

        {/* Right Action: Export CSV Button */}
        {enableExport && (
          <button
            type="button"
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-surface-subtle hover:bg-surface-subtle/80 hover:text-white transition-all border border-surface-border active:scale-[0.98]"
            aria-label="Xuất CSV"
            title="Tải xuống tệp CSV chuẩn UTF-8"
          >
            <Download className="w-3.5 h-3.5 text-brand-400" />
            <span>Xuất CSV</span>
          </button>
        )}
      </div>

      {/* Table Container */}
      <div className="rounded-xl overflow-x-auto border border-surface-border custom-scrollbar bg-[#070b14]/60">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-surface-subtle/80 border-b border-surface-border">
              {columns.map((col) => {
                const isSorted = sortColumn === col;
                return (
                  <th
                    key={col}
                    className="py-2.5 px-3 font-semibold text-slate-300 whitespace-nowrap"
                  >
                    <button
                      type="button"
                      onClick={() => handleSort(col)}
                      className="flex items-center gap-1.5 hover:text-brand-300 transition-colors focus:outline-none group"
                      aria-label={`Sắp xếp cột ${col}`}
                    >
                      <span>{col}</span>
                      {isSorted ? (
                        sortDirection === "asc" ? (
                          <ArrowUp className="w-3.5 h-3.5 text-brand-400" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-brand-400" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-500 opacity-60 group-hover:opacity-100 transition-opacity" />
                      )}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {paginatedRows.length > 0 ? (
              paginatedRows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="hover:bg-surface-subtle/40 transition-colors"
                >
                  {columns.map((col) => {
                    const value = row[col];
                    const isNumeric = typeof value === "number";
                    return (
                      <td
                        key={col}
                        className={`py-2 px-3 text-slate-200 whitespace-nowrap font-mono text-[11px] ${
                          isNumeric ? "text-emerald-300/90" : ""
                        }`}
                      >
                        {value !== null && value !== undefined
                          ? isNumeric
                            ? value.toLocaleString("vi-VN")
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
                  colSpan={columns.length}
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
              className="bg-surface-subtle border border-surface-border rounded-lg text-[11px] text-slate-300 px-2 py-0.5 focus:outline-none focus:border-brand-500/50"
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
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-subtle hover:bg-surface-subtle/80 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition-colors border border-surface-border"
              aria-label="Trang trước"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Trước</span>
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-subtle hover:bg-surface-subtle/80 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition-colors border border-surface-border"
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
