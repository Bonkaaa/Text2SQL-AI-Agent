"use client";

import React, { useState, useMemo, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Search,
  Download,
  Filter,
  Check,
  Copy,
  ChevronLeft,
  ChevronRight,
  Eye,
  RotateCcw,
  X,
  Database,
  Coins,
  FileCode,
  Terminal,
} from "lucide-react";
import { AuditLogItem } from "@/types/api";
import { exportToCsv } from "@/services/exportCsv";
import { useOptionalAppContext } from "@/context/AppContext";

export interface AuditTableProps {
  logs: AuditLogItem[];
  isLoading?: boolean;
  onRefresh?: () => void;
  title?: string;
  onExportCsv?: () => void;
  initialPageSize?: number;
}

type FilterStatus = "ALL" | "SUCCESS" | "BLOCKED_RBAC" | "BLOCKED_AST" | "BLOCKED_COST" | "OTHER";

/**
 * Format dung lượng bytes thành đơn vị hiển thị đọc được (B, KB, MB, GB).
 */
function formatBytes(bytes?: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const formatted = (bytes / Math.pow(1024, i)).toFixed(1);
  return `${formatted} ${units[i] || "B"}`;
}

/**
 * Format chuỗi thời gian ISO thành định dạng ngày giờ thân thiện tiếng Việt.
 */
function formatTimestamp(isoString?: string): string {
  if (!isoString) return "--:--:--";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return isoString;
  }
}

/**
 * Lấy cấu hình hiển thị trạng thái an ninh (màu sắc, icon, nhãn).
 */
function getStatusBadgeConfig(status: string) {
  switch (status) {
    case "SUCCESS":
      return {
        label: "Thành công",
        bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        icon: <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400 flex-shrink-0" />,
      };
    case "BLOCKED_RBAC":
      return {
        label: "Vi phạm RBAC",
        bg: "bg-rose-500/10 text-rose-400 border-rose-500/30",
        icon: <ShieldAlert className="w-3.5 h-3.5 mr-1 text-rose-400 flex-shrink-0" />,
      };
    case "BLOCKED_AST":
      return {
        label: "Chặn AST",
        bg: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        icon: <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-400 flex-shrink-0" />,
      };
    case "BLOCKED_COST":
      return {
        label: "Chặn chi phí",
        bg: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
        icon: <Coins className="w-3.5 h-3.5 mr-1 text-cyan-400 flex-shrink-0" />,
      };
    case "BLOCKED_HITL":
      return {
        label: "Chờ duyệt HITL",
        bg: "bg-purple-500/10 text-purple-400 border-purple-500/30",
        icon: <Clock className="w-3.5 h-3.5 mr-1 text-purple-400 flex-shrink-0" />,
      };
    case "TIMEOUT":
      return {
        label: "Quá thời gian",
        bg: "bg-slate-500/10 text-slate-400 border-slate-500/30",
        icon: <Clock className="w-3.5 h-3.5 mr-1 text-slate-400 flex-shrink-0" />,
      };
    case "DB_ERROR":
      return {
        label: "Lỗi DB",
        bg: "bg-red-500/10 text-red-400 border-red-500/30",
        icon: <Database className="w-3.5 h-3.5 mr-1 text-red-400 flex-shrink-0" />,
      };
    default:
      return {
        label: status || "Không rõ",
        bg: "bg-slate-500/10 text-slate-400 border-slate-500/30",
        icon: <AlertTriangle className="w-3.5 h-3.5 mr-1 text-slate-400 flex-shrink-0" />,
      };
  }
}

export function AuditTable({
  logs = [],
  isLoading = false,
  onRefresh,
  title = "Nhật ký kiểm toán an ninh (Audit Trail)",
  onExportCsv,
  initialPageSize = 10,
}: AuditTableProps) {
  const appContext = useOptionalAppContext();

  // State
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);
  const [isCopiedSql, setIsCopiedSql] = useState(false);

  // Đóng modal bằng Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && selectedLog) {
        setSelectedLog(null);
      }
    },
    [selectedLog]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Đếm số lượng theo từng nhóm trạng thái
  const counts = useMemo(() => {
    let all = logs.length;
    let success = 0;
    let rbac = 0;
    let ast = 0;
    let cost = 0;
    let other = 0;

    for (const log of logs) {
      if (log.status === "SUCCESS") success++;
      else if (log.status === "BLOCKED_RBAC") rbac++;
      else if (log.status === "BLOCKED_AST") ast++;
      else if (log.status === "BLOCKED_COST") cost++;
      else other++;
    }

    return { all, success, rbac, ast, cost, other };
  }, [logs]);

  // Lọc dữ liệu theo tab và từ khóa tìm kiếm
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      // 1. Lọc theo tab trạng thái
      if (filterStatus === "SUCCESS" && log.status !== "SUCCESS") return false;
      if (filterStatus === "BLOCKED_RBAC" && log.status !== "BLOCKED_RBAC") return false;
      if (filterStatus === "BLOCKED_AST" && log.status !== "BLOCKED_AST") return false;
      if (filterStatus === "BLOCKED_COST" && log.status !== "BLOCKED_COST") return false;
      if (
        filterStatus === "OTHER" &&
        ["SUCCESS", "BLOCKED_RBAC", "BLOCKED_AST", "BLOCKED_COST"].includes(log.status)
      ) {
        return false;
      }

      // 2. Lọc theo từ khóa tìm kiếm
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchQuestion = log.question?.toLowerCase().includes(q);
        const matchSql = log.sql?.toLowerCase().includes(q);
        const matchUser = log.user_id?.toLowerCase().includes(q);
        const matchSession = log.session_id?.toLowerCase().includes(q);
        const matchQueryId = log.query_id?.toLowerCase().includes(q);
        if (!matchQuestion && !matchSql && !matchUser && !matchSession && !matchQueryId) {
          return false;
        }
      }

      return true;
    });
  }, [logs, filterStatus, searchQuery]);

  // Reset về trang 1 khi lọc thay đổi
  useEffect(() => {
    setCurrentPage(1);
  }, [filterStatus, searchQuery, pageSize]);

  // Phân trang
  const totalItems = filteredLogs.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalItems);
  const currentLogs = useMemo(() => {
    return filteredLogs.slice(startIndex, endIndex);
  }, [filteredLogs, startIndex, endIndex]);

  // Xuất CSV
  const handleExportCsv = () => {
    if (onExportCsv) {
      onExportCsv();
      return;
    }

    const columns = [
      "Thời gian",
      "Mã phiên",
      "Mã truy vấn",
      "Người dùng",
      "Vai trò",
      "Trạng thái",
      "Thời gian xử lý (ms)",
      "Dung lượng quét (bytes)",
      "Câu hỏi",
      "Câu lệnh SQL",
      "Chi tiết lỗi",
    ];

    const rows = filteredLogs.map((log) => ({
      "Thời gian": formatTimestamp(log.created_at || log.timestamp),
      "Mã phiên": log.session_id || "",
      "Mã truy vấn": log.query_id || "",
      "Người dùng": log.user_id || "",
      "Vai trò": log.role || "",
      "Trạng thái": log.status || "",
      "Thời gian xử lý (ms)": log.execution_time_ms || 0,
      "Dung lượng quét (bytes)": log.bytes_scanned || 0,
      "Câu hỏi": log.question || "",
      "Câu lệnh SQL": log.sql || "",
      "Chi tiết lỗi": log.error_message || "",
    }));

    const dateStr = new Date().toISOString().slice(0, 10);
    exportToCsv(`nhat_ky_kiem_toan_${dateStr}`, columns, rows);

    appContext?.showToast(`Đã xuất ${rows.length} bản ghi audit ra tệp CSV`, "success");
  };

  // Sao chép SQL trong modal
  const handleCopySql = async (sql: string) => {
    if (!sql) return;
    try {
      await navigator.clipboard.writeText(sql);
      setIsCopiedSql(true);
      appContext?.showToast("Đã sao chép câu lệnh SQL vào clipboard", "success");
      setTimeout(() => setIsCopiedSql(false), 2000);
    } catch {
      appContext?.showToast("Không thể sao chép câu lệnh SQL", "error");
    }
  };

  return (
    <div className="w-full bg-[#0f111a] border border-white/10 rounded-2xl shadow-xl overflow-hidden text-slate-200">
      {/* 1. Header Toolbar */}
      <div className="p-4 sm:p-5 border-b border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#141824]/60 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-semibold text-slate-100 flex items-center gap-2">
              <span>{title}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-white/5 font-mono">
                {logs.length} bản ghi
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Kiểm toán toàn bộ truy vấn, phân quyền RBAC, kiểm tra AST và chi phí quét DuckDB
            </p>
          </div>
        </div>

        {/* Nút tác vụ nhanh */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Làm mới</span>
            </button>
          )}

          <button
            onClick={handleExportCsv}
            disabled={filteredLogs.length === 0}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Xuất CSV</span>
          </button>
        </div>
      </div>

      {/* 2. Filter Tabs & Search Bar */}
      <div className="p-4 border-b border-white/5 bg-[#121520] flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Tabs Filter */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 lg:pb-0 scrollbar-none">
          <button
            onClick={() => setFilterStatus("ALL")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 flex-shrink-0 ${
              filterStatus === "ALL"
                ? "bg-brand-500 text-white shadow-sm"
                : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
            }`}
          >
            <span>Tất cả</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-black/20 font-mono">
              {counts.all}
            </span>
          </button>

          <button
            onClick={() => setFilterStatus("SUCCESS")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 flex-shrink-0 ${
              filterStatus === "SUCCESS"
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
            }`}
          >
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>Thành công</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-black/20 font-mono">
              {counts.success}
            </span>
          </button>

          <button
            onClick={() => setFilterStatus("BLOCKED_RBAC")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 flex-shrink-0 ${
              filterStatus === "BLOCKED_RBAC"
                ? "bg-rose-600 text-white shadow-sm"
                : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
            }`}
          >
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            <span>Vi phạm RBAC</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-black/20 font-mono">
              {counts.rbac}
            </span>
          </button>

          <button
            onClick={() => setFilterStatus("BLOCKED_AST")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 flex-shrink-0 ${
              filterStatus === "BLOCKED_AST"
                ? "bg-amber-600 text-white shadow-sm"
                : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
            }`}
          >
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            <span>Chặn AST</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-black/20 font-mono">
              {counts.ast}
            </span>
          </button>

          <button
            onClick={() => setFilterStatus("BLOCKED_COST")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 flex-shrink-0 ${
              filterStatus === "BLOCKED_COST"
                ? "bg-cyan-600 text-white shadow-sm"
                : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
            }`}
          >
            <Coins className="w-3 h-3 text-cyan-400" />
            <span>Chặn chi phí</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-black/20 font-mono">
              {counts.cost}
            </span>
          </button>

          {counts.other > 0 && (
            <button
              onClick={() => setFilterStatus("OTHER")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 flex-shrink-0 ${
                filterStatus === "OTHER"
                  ? "bg-slate-600 text-white shadow-sm"
                  : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
              }`}
            >
              <span>Lỗi khác</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-black/20 font-mono">
                {counts.other}
              </span>
            </button>
          )}
        </div>

        {/* Thanh tìm kiếm nhanh */}
        <div className="relative w-full lg:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm theo câu hỏi, SQL, người dùng..."
            className="w-full pl-9 pr-8 py-1.5 rounded-xl bg-black/30 border border-white/10 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              aria-label="Xóa tìm kiếm"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-0.5"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* 3. Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.02] text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <th className="py-3 px-4">Thời gian</th>
              <th className="py-3 px-4">Người dùng</th>
              <th className="py-3 px-4">Trạng thái an ninh</th>
              <th className="py-3 px-4 min-w-[220px]">Câu hỏi tự nhiên</th>
              <th className="py-3 px-4 text-right">Thời gian</th>
              <th className="py-3 px-4 text-right">Dung lượng</th>
              <th className="py-3 px-4 text-center">Hành động</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-xs">
            {isLoading ? (
              // Loading Skeleton
              Array.from({ length: 4 }).map((_, idx) => (
                <tr key={`skeleton-${idx}`} className="animate-pulse">
                  <td className="py-3.5 px-4"><div className="h-4 bg-white/5 rounded w-24"></div></td>
                  <td className="py-3.5 px-4"><div className="h-4 bg-white/5 rounded w-20"></div></td>
                  <td className="py-3.5 px-4"><div className="h-5 bg-white/5 rounded w-28"></div></td>
                  <td className="py-3.5 px-4"><div className="h-4 bg-white/5 rounded w-48"></div></td>
                  <td className="py-3.5 px-4"><div className="h-4 bg-white/5 rounded w-12 ml-auto"></div></td>
                  <td className="py-3.5 px-4"><div className="h-4 bg-white/5 rounded w-14 ml-auto"></div></td>
                  <td className="py-3.5 px-4"><div className="h-6 bg-white/5 rounded w-16 mx-auto"></div></td>
                </tr>
              ))
            ) : currentLogs.length === 0 ? (
              // Empty State
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-slate-500">
                      <ShieldCheck className="w-6 h-6" />
                    </div>
                    <p className="text-sm font-medium text-slate-300">
                      Không có bản ghi kiểm toán nào phù hợp
                    </p>
                    <p className="text-xs text-slate-500 max-w-sm">
                      Thử thay đổi bộ lọc trạng thái hoặc từ khóa tìm kiếm để xem kết quả.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              currentLogs.map((log) => {
                const statusBadge = getStatusBadgeConfig(log.status);
                const isAnalyst = log.role?.toLowerCase() === "analyst";

                return (
                  <tr
                    key={log.query_id || `${log.session_id}-${log.created_at || log.timestamp}`}
                    className="hover:bg-white/[0.03] transition-colors group cursor-pointer"
                    onClick={() => setSelectedLog(log)}
                  >
                    {/* Cột thời gian */}
                    <td className="py-3 px-4 font-mono text-slate-400 whitespace-nowrap">
                      {formatTimestamp(log.created_at || log.timestamp)}
                    </td>

                    {/* Cột người dùng & vai trò */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-slate-200">{log.user_id}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.2 rounded font-semibold border ${
                            isAnalyst
                              ? "bg-brand-500/15 text-brand-300 border-brand-500/30"
                              : "bg-amber-500/15 text-amber-300 border-amber-500/30"
                          }`}
                        >
                          {log.role}
                        </span>
                      </div>
                    </td>

                    {/* Cột trạng thái */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${statusBadge.bg}`}
                      >
                        {statusBadge.icon}
                        {statusBadge.label}
                      </span>
                    </td>

                    {/* Cột câu hỏi */}
                    <td className="py-3 px-4 text-slate-300 max-w-xs truncate" title={log.question}>
                      {log.question || "--"}
                    </td>

                    {/* Cột thời gian xử lý */}
                    <td className="py-3 px-4 text-right font-mono text-slate-400 whitespace-nowrap">
                      {log.execution_time_ms ? `${log.execution_time_ms.toFixed(1)}ms` : "0.0ms"}
                    </td>

                    {/* Cột dung lượng quét */}
                    <td className="py-3 px-4 text-right font-mono text-slate-400 whitespace-nowrap">
                      {formatBytes(log.bytes_scanned)}
                    </td>

                    {/* Nút hành động */}
                    <td className="py-3 px-4 text-center whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => setSelectedLog(log)}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white transition-colors inline-flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Chi tiết</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* 4. Pagination Footer */}
      <div className="p-4 border-t border-white/10 bg-[#121520] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span>
            Hiển thị {totalItems === 0 ? 0 : startIndex + 1} - {endIndex} của {totalItems} bản ghi
          </span>
          <span className="text-slate-600">•</span>
          <div className="flex items-center gap-1.5">
            <span>Dòng/trang:</span>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>

        {/* Nút lật trang */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            aria-label="Trang trước"
            className="p-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 disabled:opacity-40 disabled:pointer-events-none transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="px-3 py-1 font-mono text-slate-300 font-semibold">
            {currentPage} / {totalPages}
          </span>

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages || totalPages === 0}
            aria-label="Trang sau"
            className="p-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 disabled:opacity-40 disabled:pointer-events-none transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 5. Detail Modal (Accessible Dialog) */}
      {selectedLog && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="audit-detail-title"
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="w-full max-w-2xl bg-[#141824] border border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-4 sm:p-5 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <h3 id="audit-detail-title" className="text-sm sm:text-base font-semibold text-slate-100">
                    Chi tiết truy vấn kiểm toán
                  </h3>
                  <div className="text-[11px] text-slate-400 font-mono">
                    Session: {selectedLog.session_id} | Query: {selectedLog.query_id || "N/A"}
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedLog(null)}
                aria-label="Đóng modal"
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 overflow-y-auto">
              {/* Thông tin Meta */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs bg-white/[0.02] p-3 rounded-xl border border-white/5">
                <div>
                  <div className="text-slate-500 text-[10px] uppercase font-semibold">Người dùng</div>
                  <div className="font-medium text-slate-200 mt-0.5">{selectedLog.user_id}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px] uppercase font-semibold">Vai trò</div>
                  <div className="font-medium text-slate-200 mt-0.5">{selectedLog.role}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px] uppercase font-semibold">Thời gian xử lý</div>
                  <div className="font-mono text-slate-200 mt-0.5">
                    {selectedLog.execution_time_ms ? `${selectedLog.execution_time_ms.toFixed(1)}ms` : "0.0ms"}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px] uppercase font-semibold">Dung lượng quét</div>
                  <div className="font-mono text-slate-200 mt-0.5">{formatBytes(selectedLog.bytes_scanned)}</div>
                </div>
              </div>

              {/* Trạng thái an ninh */}
              <div>
                <div className="text-xs font-semibold text-slate-400 mb-1.5">Trạng thái an ninh & kiểm duyệt</div>
                <div>
                  {(() => {
                    const badge = getStatusBadgeConfig(selectedLog.status);
                    return (
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.bg}`}
                      >
                        {badge.icon}
                        {badge.label}
                      </span>
                    );
                  })()}
                </div>
              </div>

              {/* Câu hỏi tự nhiên */}
              <div>
                <div className="text-xs font-semibold text-slate-400 mb-1.5">Câu hỏi tự nhiên của người dùng</div>
                <div className="p-3 rounded-xl bg-black/40 border border-white/10 text-xs text-slate-200 leading-relaxed">
                  {selectedLog.question || "Không có câu hỏi ghi nhận"}
                </div>
              </div>

              {/* Câu lệnh SQL */}
              {selectedLog.sql && (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-brand-400" />
                      <span>Câu lệnh SQL thực thi / kiểm duyệt</span>
                    </span>

                    <button
                      onClick={() => handleCopySql(selectedLog.sql || "")}
                      className="px-2 py-1 rounded text-[11px] font-medium bg-white/5 hover:bg-white/10 text-slate-300 flex items-center gap-1 transition-colors"
                    >
                      {isCopiedSql ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-300">Đã chép</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Sao chép SQL</span>
                        </>
                      )}
                    </button>
                  </div>

                  <pre className="p-3 rounded-xl bg-black/50 border border-white/10 text-xs font-mono text-emerald-300 overflow-x-auto leading-relaxed whitespace-pre-wrap">
                    {selectedLog.sql}
                  </pre>
                </div>
              )}

              {/* Chi tiết lỗi nếu có */}
              {selectedLog.error_message && (
                <div>
                  <div className="text-xs font-semibold text-rose-400 mb-1.5 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Chi tiết vi phạm / Thông báo lỗi hệ thống</span>
                  </div>
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-200 leading-relaxed">
                    {selectedLog.error_message}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-white/10 bg-white/[0.02] flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-xl text-xs font-medium bg-white/10 hover:bg-white/15 text-slate-200 transition-colors"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
