"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  BrainCircuit,
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Copy,
  Database,
  Download,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import { ChatMessage, QueryResponse } from "@/types/api";
import { exportToCsv } from "@/services/exportCsv";
import { useAppContext } from "@/context/AppContext";

interface ChatMessageItemProps {
  message: ChatMessage;
  onApproveHitl?: (approved: boolean) => void;
}

export function ChatMessageItem({
  message,
  onApproveHitl,
}: ChatMessageItemProps) {
  const { showToast } = useAppContext();
  const isUser = message.role === "user";
  const response: QueryResponse | undefined = message.queryResponse;

  const [isCopiedSql, setIsCopiedSql] = useState(false);
  const [isReasoningOpen, setIsReasoningOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"table" | "sql">("table");
  const [page, setPage] = useState(1);
  const pageSize = 5;

  const handleCopySql = () => {
    if (!response?.sql) return;
    navigator.clipboard.writeText(response.sql);
    setIsCopiedSql(true);
    showToast("Đã sao chép câu lệnh SQL vào clipboard", "success", 2000);
    setTimeout(() => setIsCopiedSql(false), 2000);
  };

  const handleExport = () => {
    if (!response?.data || !response.columns) return;
    const filename = `query_result_${new Date().getTime()}`;
    exportToCsv(filename, response.columns, response.data);
    showToast("Đã tải xuống tệp dữ liệu CSV", "success", 2000);
  };

  // User Message
  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3 my-4 animate-in fade-in duration-200">
        <div className="max-w-xl bg-brand-600/90 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-md border border-brand-500/30">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          <div className="text-[10px] text-brand-200/80 mt-1.5 text-right font-mono">
            {new Date(message.timestamp).toLocaleTimeString("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
        <div className="w-8 h-8 rounded-xl bg-surface-subtle border border-surface-border flex items-center justify-center text-slate-300 flex-shrink-0">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // Assistant Message (Loading State)
  if (message.isLoading) {
    return (
      <div className="flex items-start gap-3 my-4 animate-in fade-in duration-200">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 text-white flex items-center justify-center flex-shrink-0 shadow-glow">
          <Sparkles className="w-4 h-4 animate-pulse" />
        </div>
        <div className="glass-card rounded-2xl rounded-tl-sm p-4 w-full max-w-2xl border border-surface-border">
          <div className="flex items-center gap-2 text-xs text-brand-300 font-medium mb-2">
            <BrainCircuit className="w-4 h-4 animate-spin text-brand-400" />
            <span>DeepAgents Supervisor đang phân tích câu hỏi & định tuyến schema...</span>
          </div>
          <div className="space-y-2">
            <div className="h-3 bg-surface-subtle rounded-full w-3/4 animate-pulse" />
            <div className="h-3 bg-surface-subtle rounded-full w-1/2 animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  // Assistant Completed Message
  const hasData = response?.data && response.data.length > 0;
  const totalRows = response?.data?.length || 0;
  const paginatedRows =
    response?.data?.slice((page - 1) * pageSize, page * pageSize) || [];
  const totalPages = Math.ceil(totalRows / pageSize);

  return (
    <div className="flex items-start gap-3 my-5 animate-in fade-in duration-200">
      {/* Bot Avatar */}
      <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 text-white flex items-center justify-center flex-shrink-0 shadow-glow mt-1">
        <Sparkles className="w-4 h-4" />
      </div>

      <div className="glass-card rounded-2xl rounded-tl-sm p-4 sm:p-5 w-full max-w-3xl border border-surface-border space-y-4 shadow-card">
        {/* Header bar of Assistant response */}
        <div className="flex items-center justify-between border-b border-surface-border pb-2.5 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-200">DeepAgents TPC-H</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-brand-500/15 text-brand-300 border border-brand-500/20 font-medium">
              AST Verified
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px] text-slate-400">
            {response?.execution_time_ms !== undefined && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />
                <span>{response.execution_time_ms}ms</span>
              </span>
            )}
            {hasData && (
              <span className="flex items-center gap-1 font-mono">
                <Database className="w-3 h-3 text-emerald-400" />
                <span>{totalRows} bản ghi</span>
              </span>
            )}
          </div>
        </div>

        {/* 1. Reasoning CoT Accordion */}
        <div className="rounded-xl border border-surface-border bg-surface-subtle/30 overflow-hidden">
          <button
            onClick={() => setIsReasoningOpen(!isReasoningOpen)}
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-surface-subtle/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-3.5 h-3.5 text-brand-400" />
              <span>Quy trình suy luận (DeepAgents CoT)</span>
            </div>
            {isReasoningOpen ? (
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            )}
          </button>

          {isReasoningOpen && (
            <div className="p-3 border-t border-surface-border space-y-2 text-xs text-slate-300">
              <div className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold text-slate-200">1. Làm rõ ý định:</span> Xác định câu hỏi không mơ hồ, ngữ cảnh phân tích hợp lệ.
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 mt-1.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold text-slate-200">2. Schema Retriever:</span> Lấy ngữ cảnh bảng liên quan trong 8 bảng TPC-H.
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold text-slate-200">3. SQL Generator:</span> Tạo câu truy vấn chuẩn ANSI SQL và tương thích DuckDB.
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold text-slate-200">4. LangGraph Control Guard:</span> AST Sanitizer kiểm tra an toàn (chỉ cho phép SELECT).
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 2. Natural Language Explanation / Final Answer */}
        {response?.final_answer && (
          <div className="text-sm text-slate-200 leading-relaxed font-normal bg-surface/60 p-3.5 rounded-xl border border-surface-border">
            {response.final_answer}
          </div>
        )}

        {/* 3. Tab Switcher: Data Table vs SQL Code */}
        {response?.sql && (
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-surface-border pb-2">
              <div className="flex items-center gap-2">
                {hasData && (
                  <button
                    onClick={() => setActiveTab("table")}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                      activeTab === "table"
                        ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Bảng kết quả
                  </button>
                )}
                <button
                  onClick={() => setActiveTab("sql")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                    activeTab === "sql" || !hasData
                      ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Truy vấn SQL
                </button>
              </div>

              {activeTab === "table" && hasData && (
                <button
                  onClick={handleExport}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-300 bg-surface-subtle hover:bg-surface-subtle/80 hover:text-white transition-all border border-surface-border"
                  title="Xuất file CSV"
                >
                  <Download className="w-3.5 h-3.5 text-brand-400" />
                  <span>Xuất CSV</span>
                </button>
              )}

              {activeTab === "sql" && (
                <button
                  onClick={handleCopySql}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-300 bg-surface-subtle hover:bg-surface-subtle/80 hover:text-white transition-all border border-surface-border"
                >
                  {isCopiedSql ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Đã chép</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Sao chép SQL</span>
                    </>
                  )}
                </button>
              )}
            </div>

            {/* Content: SQL View */}
            {(activeTab === "sql" || !hasData) && response.sql && (
              <div className="relative rounded-xl overflow-hidden border border-surface-border bg-[#0a0f1d] p-3.5">
                <pre className="text-xs font-mono text-indigo-300 overflow-x-auto custom-scrollbar leading-relaxed">
                  <code>{response.sql}</code>
                </pre>
              </div>
            )}

            {/* Content: Data Table View */}
            {activeTab === "table" && hasData && response.columns && (
              <div className="space-y-3">
                <div className="rounded-xl overflow-x-auto border border-surface-border custom-scrollbar">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-surface-subtle/70 border-b border-surface-border">
                        {response.columns.map((col) => (
                          <th
                            key={col}
                            className="py-2.5 px-3 font-semibold text-slate-300 whitespace-nowrap"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border">
                      {paginatedRows.map((row, idx) => (
                        <tr
                          key={idx}
                          className="hover:bg-surface-subtle/40 transition-colors"
                        >
                          {response.columns!.map((col) => (
                            <td
                              key={col}
                              className="py-2 px-3 text-slate-200 whitespace-nowrap font-mono text-[11px]"
                            >
                              {row[col] !== null && row[col] !== undefined
                                ? String(row[col])
                                : "-"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                    <span>
                      Trang {page} / {totalPages} (Tổng {totalRows} dòng)
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="px-2.5 py-1 rounded bg-surface-subtle hover:bg-surface-subtle/80 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200"
                      >
                        Trước
                      </button>
                      <button
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="px-2.5 py-1 rounded bg-surface-subtle hover:bg-surface-subtle/80 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200"
                      >
                        Sau
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 4. HITL Approval Request Banner (nếu cần phê duyệt) */}
        {response?.requires_hitl && onApproveHitl && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-3">
            <div className="flex items-start gap-2.5 text-amber-300 text-xs font-medium">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold text-amber-200">
                  Cảnh báo chi phí truy vấn (HITL Required)
                </div>
                <div className="text-amber-300/80 mt-0.5">
                  Truy vấn ước lượng quét qua lượng dữ liệu lớn ({response.estimated_cost_bytes || 0} bytes). Bạn có đồng ý thực thi không?
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={() => onApproveHitl(true)}
                className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-sm transition-all"
              >
                Phê duyệt thực thi
              </button>
              <button
                onClick={() => onApproveHitl(false)}
                className="px-3 py-1.5 rounded-lg bg-surface-subtle hover:bg-surface-subtle/80 text-slate-300 text-xs font-medium border border-surface-border transition-all"
              >
                Từ chối
              </button>
            </div>
          </div>
        )}

        {/* 5. Error Banner */}
        {response?.error && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-semibold text-rose-200">Lỗi thực thi câu truy vấn</div>
              <div className="text-rose-300/90 leading-relaxed font-mono text-[11px]">
                {response.error}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
