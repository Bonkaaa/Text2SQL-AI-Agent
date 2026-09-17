"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Calculator,
  ChevronDown,
  ChevronRight,
  Copy,
  Database,
  Key,
  Link2,
  Search,
  ShieldAlert,
  Sparkles,
  Table,
  X,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";
import {
  SEMANTIC_METRICS,
  TableDefinition,
  TPCH_TABLES,
} from "@/data/tpchSchema";

export function SchemaDrawer() {
  const { isSchemaDrawerOpen, setSchemaDrawerOpen, currentRole, showToast } =
    useAppContext();

  const [activeTab, setActiveTab] = useState<"tables" | "metrics">("tables");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTableName, setExpandedTableName] = useState<string | null>(
    "lineitem"
  );

  const isAnalyst = currentRole === "ANALYST" || currentRole === "Analyst";

  // Đóng Drawer khi bấm phím Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isSchemaDrawerOpen) {
        setSchemaDrawerOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSchemaDrawerOpen, setSchemaDrawerOpen]);

  // Bộ lọc tìm kiếm bảng và cột
  const filteredTables = useMemo(() => {
    if (!searchQuery.trim()) return TPCH_TABLES;
    const query = searchQuery.toLowerCase().trim();

    return TPCH_TABLES.filter(
      (t) =>
        t.name.toLowerCase().includes(query) ||
        t.displayName.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query) ||
        t.columns.some(
          (c) =>
            c.name.toLowerCase().includes(query) ||
            c.description.toLowerCase().includes(query)
        )
    );
  }, [searchQuery]);

  // Bộ lọc tìm kiếm công thức chỉ số
  const filteredMetrics = useMemo(() => {
    if (!searchQuery.trim()) return SEMANTIC_METRICS;
    const query = searchQuery.toLowerCase().trim();

    return SEMANTIC_METRICS.filter(
      (m) =>
        m.name.toLowerCase().includes(query) ||
        m.businessMeaning.toLowerCase().includes(query) ||
        m.formulaSql.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  const handleCopyFormula = (formula: string, name: string) => {
    navigator.clipboard.writeText(formula);
    showToast(`Đã sao chép công thức: "${name}"`, "success", 2500);
  };

  return (
    <>
      {/* ================================================================= */}
      {/* 1. BACKDROP OVERLAY */}
      {/* ================================================================= */}
      <div
        className={`fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity duration-300 ease-in-out ${
          isSchemaDrawerOpen
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setSchemaDrawerOpen(false)}
        aria-hidden={!isSchemaDrawerOpen}
      />

      {/* ================================================================= */}
      {/* 2. DRAWER SIDE PANEL (SLIDE IN/OUT) */}
      {/* ================================================================= */}
      <aside
        aria-hidden={!isSchemaDrawerOpen}
        className={`fixed inset-y-0 right-0 z-50 flex w-full sm:w-[480px] lg:w-[520px] flex-col bg-surface/95 border-l border-surface-border shadow-2xl backdrop-blur-2xl transition-transform duration-300 ease-in-out transform ${
          isSchemaDrawerOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* HEADER */}
        <div className="flex items-center justify-between border-b border-surface-border p-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Lược đồ dữ liệu TPC-H</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-surface-subtle text-slate-400 border border-surface-border">
                  8 Bảng
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Chuẩn TPC-H Wholesale & Supply Chain Benchmark
              </p>
            </div>
          </div>

          <button
            onClick={() => setSchemaDrawerOpen(false)}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-surface-subtle transition-colors"
            title="Đóng (Escape)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* SEARCH & TAB SWITCHER */}
        <div className="p-4 space-y-3 border-b border-surface-border bg-surface-subtle/30">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm bảng, tên cột (ví dụ: revenue, phone)..."
              className="w-full pl-9 pr-8 py-2 bg-surface/80 border border-surface-border rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500/50 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Tab Selector */}
          <div className="flex rounded-xl bg-surface-subtle/80 p-1 border border-surface-border">
            <button
              onClick={() => setActiveTab("tables")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "tables"
                  ? "bg-brand-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Table className="w-3.5 h-3.5" />
              <span>8 Bảng Dữ Liệu</span>
            </button>

            <button
              onClick={() => setActiveTab("metrics")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "metrics"
                  ? "bg-brand-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Calculator className="w-3.5 h-3.5" />
              <span>Chỉ Số Nghiệp Vụ</span>
            </button>
          </div>
        </div>

        {/* CONTENT SCROLL AREA */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
          {activeTab === "tables" ? (
            /* ============================================================= */
            /* TAB 1: DANH SÁCH 8 BẢNG TPC-H */
            /* ============================================================= */
            filteredTables.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                Không tìm thấy bảng hoặc cột nào khớp với &quot;{searchQuery}&quot;
              </div>
            ) : (
              <div className="space-y-2.5">
                {filteredTables.map((table: TableDefinition) => {
                  const isExpanded = expandedTableName === table.name;
                  const hasPii = table.columns.some((c) => c.isPii);

                  return (
                    <div
                      key={table.name}
                      className="rounded-xl border border-surface-border bg-surface-subtle/40 overflow-hidden transition-all"
                    >
                      {/* Table Header Button */}
                      <button
                        onClick={() =>
                          setExpandedTableName(isExpanded ? null : table.name)
                        }
                        className="w-full flex items-center justify-between p-3 text-left hover:bg-surface-subtle/80 transition-colors"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="p-1.5 rounded-lg bg-surface text-brand-400 border border-surface-border flex-shrink-0">
                            <Table className="w-4 h-4" />
                          </div>
                          <div className="truncate">
                            <div className="text-xs font-bold text-slate-200 flex items-center gap-2">
                              <span>{table.name}</span>
                              <span className="text-[10px] font-normal text-slate-400">
                                ({table.displayName})
                              </span>
                              {hasPii && (
                                <span
                                  className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[9px] font-semibold border border-amber-500/20"
                                  title="Bảng có chứa cột thông tin cá nhân PII"
                                >
                                  Chứa PII
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-400 truncate mt-0.5">
                              {table.description}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                          <span className="text-[10px] font-mono text-slate-400 hidden sm:inline">
                            {table.columns.length} cột
                          </span>
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-slate-400" />
                          )}
                        </div>
                      </button>

                      {/* Expanded Columns List */}
                      {isExpanded && (
                        <div className="p-3 border-t border-surface-border/60 bg-surface/50 space-y-2">
                          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                            <span>Danh sách cột dữ liệu</span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {table.estimatedRows}
                            </span>
                          </div>

                          <div className="divide-y divide-surface-border/40">
                            {table.columns.map((col) => (
                              <div
                                key={col.name}
                                className="py-2 flex items-start justify-between gap-2 text-xs"
                              >
                                <div className="space-y-0.5 min-w-0">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="font-mono font-semibold text-slate-200">
                                      {col.name}
                                    </span>
                                    <span className="text-[10px] font-mono px-1 rounded bg-surface text-slate-400 border border-surface-border">
                                      {col.type}
                                    </span>
                                    {col.isPk && (
                                      <span className="flex items-center gap-0.5 text-[9px] px-1 rounded bg-brand-500/10 text-brand-300 font-semibold border border-brand-500/20">
                                        <Key className="w-2.5 h-2.5" /> PK
                                      </span>
                                    )}
                                    {col.isFk && (
                                      <span
                                        className="flex items-center gap-0.5 text-[9px] px-1 rounded bg-slate-800 text-slate-300 font-semibold border border-surface-border"
                                        title={`Khóa ngoại trỏ đến: ${col.fkTarget}`}
                                      >
                                        <Link2 className="w-2.5 h-2.5 text-brand-400" /> FK
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-[11px] text-slate-400 leading-snug">
                                    {col.description}
                                  </div>
                                </div>

                                {/* PII RBAC Warning Badge */}
                                {col.isPii && (
                                  <div className="flex-shrink-0">
                                    <span
                                      className={`inline-flex items-center gap-1 text-[9px] font-semibold px-2 py-0.5 rounded-full border ${
                                        isAnalyst
                                          ? "bg-danger/10 text-danger border-danger/30"
                                          : "bg-amber-500/10 text-amber-300 border-amber-500/30"
                                      }`}
                                      title={
                                        isAnalyst
                                          ? "Cột này bị chặn 100% khi người dùng ở vai trò Analyst."
                                          : "Cột nhạy cảm (Được phép truy cập với quyền Admin)."
                                      }
                                    >
                                      <ShieldAlert className="w-3 h-3" />
                                      <span>{isAnalyst ? "Bị chặn PII" : "Cột PII"}</span>
                                    </span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )
          ) : (
            /* ============================================================= */
            /* TAB 2: CÔNG THỨC CHỈ SỐ NGHIỆP VỤ (dbt Metrics) */
            /* ============================================================= */
            filteredMetrics.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                Không tìm thấy chỉ số nào khớp với &quot;{searchQuery}&quot;
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-brand-500/10 border border-brand-500/20 text-xs text-brand-300 flex items-start gap-2.5">
                  <Sparkles className="w-4 h-4 text-brand-400 flex-shrink-0 mt-0.5" />
                  <div className="leading-relaxed">
                    Đây là các <strong>công thức dbt Semantic Layer chuẩn</strong>.
                    Khi người dùng hỏi bằng tiếng Việt, Agent sẽ tự động áp dụng các
                    công thức này để sinh ra câu lệnh SQL chính xác.
                  </div>
                </div>

                {filteredMetrics.map((metric) => (
                  <div
                    key={metric.id}
                    className="p-3.5 rounded-xl border border-surface-border bg-surface-subtle/40 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="text-xs font-bold text-slate-200">
                          {metric.name}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                          {metric.businessMeaning}
                        </div>
                      </div>
                      <button
                        onClick={() =>
                          handleCopyFormula(metric.formulaSql, metric.name)
                        }
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-subtle transition-colors flex-shrink-0"
                        title="Sao chép biểu thức SQL"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* SQL Formula Snippet */}
                    <div className="p-2 rounded-lg bg-surface border border-surface-border font-mono text-[11px] text-brand-300 break-all">
                      <code>{metric.formulaSql}</code>
                    </div>

                    <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                      <span>Bảng liên quan:</span>
                      {metric.tablesUsed.map((tbl) => (
                        <span
                          key={tbl}
                          className="px-1.5 py-0.2 rounded bg-surface border border-surface-border text-slate-300 font-mono"
                        >
                          {tbl}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* FOOTER NOTICE */}
        <div className="p-3 border-t border-surface-border bg-surface-subtle/40 text-[11px] text-slate-400 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-success"></span>
            <span>Kho dữ liệu DuckDB TPC-H Active</span>
          </div>
          <span className="font-mono text-[10px] text-slate-400">
            Esc để đóng
          </span>
        </div>
      </aside>
    </>
  );
}
