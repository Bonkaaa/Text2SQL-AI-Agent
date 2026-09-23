"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  ShieldCheck,
  ArrowLeft,
  RotateCcw,
  AlertTriangle,
  Activity,
  Lock,
  Coins,
  RefreshCw,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";
import { getAuditLogs } from "@/services/api";
import { AuditLogItem } from "@/types/api";
import { AuditTable } from "@/components/admin/AuditTable";

export default function AuditPage() {
  const { currentRole, setCurrentRole, showToast } = useAppContext();

  // State
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = currentRole === "Admin";

  // Hàm tải danh sách audit logs
  const fetchLogs = useCallback(async () => {
    if (!isAdmin) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await getAuditLogs(100, 0, "Admin");
      setLogs(response.logs || []);
    } catch (err: any) {
      const errorMessage =
        err?.message || "Không thể tải nhật ký kiểm toán từ máy chủ backend.";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [isAdmin]);

  // Nạp dữ liệu khi vào trang với quyền Admin
  useEffect(() => {
    if (isAdmin) {
      fetchLogs();
    }
  }, [isAdmin, fetchLogs]);

  // Xử lý làm mới thủ công
  const handleManualRefresh = async () => {
    await fetchLogs();
    showToast?.("Đã làm mới dữ liệu kiểm toán hệ thống", "info");
  };

  // Tính toán số liệu thống kê KPI
  const metrics = useMemo(() => {
    const total = logs.length;
    let successCount = 0;
    let rbacCount = 0;
    let astCount = 0;
    let costCount = 0;

    for (const log of logs) {
      if (log.status === "SUCCESS") successCount++;
      else if (log.status === "BLOCKED_RBAC") rbacCount++;
      else if (log.status === "BLOCKED_AST") astCount++;
      else if (log.status === "BLOCKED_COST") costCount++;
    }

    const successRate = total > 0 ? Math.round((successCount / total) * 100) : 0;
    const astCostCount = astCount + costCount;

    return {
      total,
      successCount,
      successRate,
      rbacCount,
      astCount,
      costCount,
      astCostCount,
    };
  }, [logs]);

  // ============================================================================
  // 1. ROLE GATE: CẢNH BÁO 403 FORBIDDEN NẾU NGƯỜI DÙNG LÀ ANALYST
  // ============================================================================
  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-[#090d19] text-slate-100 flex flex-col items-center justify-center p-6 select-none">
        <div className="max-w-lg w-full bg-[#111522] border border-rose-500/25 rounded-3xl p-8 shadow-2xl shadow-rose-950/20 text-center space-y-6 animate-in fade-in zoom-in-95 duration-200">
          {/* Icon Khiên Cảnh Báo */}
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400">
            <ShieldAlert className="w-8 h-8 animate-pulse" />
          </div>

          <div className="space-y-2">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold uppercase tracking-wider">
              <span>403 Forbidden</span>
              <span>•</span>
              <span>Access Denied</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Truy cập bị hạn chế (403 Forbidden)
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Trang Nhật ký Kiểm toán chỉ dành riêng cho vai trò Quản trị viên (
              <strong className="text-slate-200">Admin - Trần Thị Bình</strong>). Vai trò hiện tại của
              bạn là Analyst (<strong className="text-slate-200">Nguyễn Văn An</strong>) không có thẩm
              quyền xem nhật ký bảo mật của hệ thống.
            </p>
          </div>

          {/* Nút hành động */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/"
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white transition-colors flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Quay về trang phân tích</span>
            </Link>

            <button
              onClick={() => {
                setCurrentRole("Admin");
                showToast?.("Đã chuyển sang vai trò: Admin (Trần Thị Bình)", "info");
              }}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Chuyển sang vai trò Admin</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // 2. ADMIN AUDIT VIEW: DÀNH CHO VAI TRÒ ADMIN (TRẦN THỊ BÌNH)
  // ============================================================================
  return (
    <div className="min-h-screen bg-[#090d19] text-slate-100 flex flex-col selection:bg-brand-500/30 selection:text-brand-200">
      {/* TopBar Navigation */}
      <header className="sticky top-0 z-40 bg-[#0c101d]/90 backdrop-blur-md border-b border-white/10 px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Quay về phân tích</span>
            <span className="sm:hidden">Trang chủ</span>
          </Link>

          <div>
            <h1 className="text-sm sm:text-base font-bold text-slate-100 flex items-center gap-2">
              <span>Trung tâm Quản trị & Kiểm toán An ninh</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold uppercase">
                Admin
              </span>
            </h1>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Giám sát thời gian thực mọi truy vấn SQL, phân quyền RBAC và kiểm soát chi phí DuckDB
            </p>
          </div>
        </div>

        {/* Nút Làm mới & Vai trò */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleManualRefresh}
            disabled={isLoading}
            aria-label="Làm mới dữ liệu"
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Làm mới dữ liệu</span>
          </button>

          <div className="flex items-center gap-2 pl-2 border-l border-white/10">
            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-amber-500 to-orange-500 text-white font-bold text-[11px] flex items-center justify-center ring-2 ring-white/10">
              TB
            </div>
            <div className="text-xs hidden md:block">
              <div className="font-semibold text-slate-200">Trần Thị Bình</div>
              <div className="text-[10px] text-amber-400">Data Lead & Admin</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 p-4 sm:p-8 max-w-7xl mx-auto w-full space-y-6">
        {/* Error Alert nếu có lỗi kết nối */}
        {error && (
          <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <div>
                <strong className="font-semibold text-rose-200">
                  Không thể tải nhật ký kiểm toán:
                </strong>{" "}
                {error}
              </div>
            </div>
            <button
              onClick={fetchLogs}
              className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-medium transition-colors flex items-center gap-1 flex-shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử lại</span>
            </button>
          </div>
        )}

        {/* 4 Thẻ KPI Thống Kê Kiểm Toán */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {/* KPI 1: Tổng số truy vấn */}
          <div className="bg-[#111522] border border-white/10 rounded-2xl p-4 sm:p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Tổng số truy vấn
              </div>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-white">
                {metrics.total}
              </div>
              <div className="text-[11px] text-slate-500">Lượt ghi vết kiểm toán</div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <Activity className="w-5 h-5" />
            </div>
          </div>

          {/* KPI 2: Tỷ lệ thành công */}
          <div className="bg-[#111522] border border-white/10 rounded-2xl p-4 sm:p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Tỷ lệ thành công
              </div>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-emerald-400">
                {metrics.successRate}%
              </div>
              <div className="text-[11px] text-emerald-500/80">
                {metrics.successCount} truy vấn an toàn
              </div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>

          {/* KPI 3: Vi phạm RBAC */}
          <div className="bg-[#111522] border border-white/10 rounded-2xl p-4 sm:p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Vi phạm RBAC
              </div>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-rose-400">
                {metrics.rbacCount}
              </div>
              <div className="text-[11px] text-rose-500/80">Chặn truy cập cột nhạy cảm</div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <Lock className="w-5 h-5" />
            </div>
          </div>

          {/* KPI 4: Chặn AST & Chi phí */}
          <div className="bg-[#111522] border border-white/10 rounded-2xl p-4 sm:p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Chặn AST & Chi phí
              </div>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-amber-400">
                {metrics.astCostCount}
              </div>
              <div className="text-[11px] text-amber-500/80">
                {metrics.astCount} AST • {metrics.costCount} Cost
              </div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Coins className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Bảng Nhật Ký Kiểm Toán (Component 5.1: AuditTable) */}
        <AuditTable logs={logs} isLoading={isLoading} onRefresh={fetchLogs} />
      </main>
    </div>
  );
}
