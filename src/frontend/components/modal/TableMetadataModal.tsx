"use client";

import React, { useEffect } from "react";
import {
  X,
  Database,
  Key,
  Calendar,
  Layers,
  Lock,
  MessageSquarePlus,
} from "lucide-react";
import { getTableDetails } from "../../data/tpcdsCatalog";

export interface TableMetadataModalProps {
  isOpen: boolean;
  tableName: string | null;
  onClose: () => void;
  onSelectForPrompt?: (tableName: string) => void;
}

export function TableMetadataModal({
  isOpen,
  tableName,
  onClose,
  onSelectForPrompt,
}: TableMetadataModalProps) {
  // Lắng nghe sự kiện Escape để đóng modal
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !tableName) {
    return null;
  }

  const table = getTableDetails(tableName);

  const handleSelectTable = () => {
    if (onSelectForPrompt) {
      onSelectForPrompt(tableName);
    }
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-table-title"
        className="bg-[#0a0f1d] border border-border-default/80 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-default/60 bg-surface-secondary/40">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-primary-500/10 text-primary-400 border border-primary-500/20">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3
                  id="modal-table-title"
                  className="text-sm font-bold text-white font-mono-data tracking-wide"
                >
                  {tableName}
                </h3>
                {table?.category && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-surface-secondary text-primary-300 border border-border-default/60">
                    {table.category}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {table?.label || "Lược đồ bảng TPC-DS Benchmark"}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng modal"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-secondary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 overflow-y-auto custom-scrollbar flex-1 text-xs">
          {/* Business Description */}
          {table?.description && (
            <div className="p-3 rounded-xl bg-surface-secondary/50 border border-border-default/60 text-slate-300 leading-relaxed">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Mô tả nghiệp vụ
              </span>
              <p>{table.description}</p>
            </div>
          )}

          {/* Key Lineage Attributes */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {/* Primary Key */}
            <div className="p-2.5 rounded-xl bg-surface-secondary/40 border border-border-default/50 space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-400 uppercase">
                <Key className="w-3 h-3 text-amber-400" />
                <span>Khóa chính (PK)</span>
              </div>
              <div className="font-mono-data text-[11px] text-slate-200">
                {table?.primaryKey?.join(", ") || "—"}
              </div>
            </div>

            {/* Date Dimension Key */}
            <div className="p-2.5 rounded-xl bg-surface-secondary/40 border border-border-default/50 space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-400 uppercase">
                <Calendar className="w-3 h-3 text-blue-400" />
                <span>Khóa ngày tháng</span>
              </div>
              <div className="font-mono-data text-[11px] text-slate-200">
                {table?.dateKey || "Không áp dụng"}
              </div>
            </div>

            {/* Common Joins */}
            <div className="p-2.5 rounded-xl bg-surface-secondary/40 border border-border-default/50 space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-400 uppercase">
                <Layers className="w-3 h-3 text-emerald-400" />
                <span>Liên kết phổ biến</span>
              </div>
              <div className="font-mono-data text-[11px] text-slate-200 truncate">
                {table?.commonJoins?.join(", ") || "—"}
              </div>
            </div>
          </div>

          {/* Column Schema Table */}
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Danh sách cột & kiểu dữ liệu ({table?.columns?.length || 0} cột)
            </span>
            <div className="rounded-xl border border-border-default/60 overflow-hidden bg-surface-primary/40">
              <div className="overflow-x-auto custom-scrollbar max-h-56">
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead className="sticky top-0 bg-surface-secondary/90 backdrop-blur-md border-b border-border-default/60 text-slate-400">
                    <tr>
                      <th className="py-2 px-3 font-semibold">Tên cột</th>
                      <th className="py-2 px-3 font-semibold">Kiểu dữ liệu</th>
                      <th className="py-2 px-3 font-semibold">Đặc tính</th>
                      <th className="py-2 px-3 font-semibold">Mô tả</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-default/40 text-slate-300">
                    {table?.columns?.map((col) => (
                      <tr
                        key={col.name}
                        className="hover:bg-surface-secondary/30 transition-colors"
                      >
                        <td className="py-2 px-3 font-mono-data font-medium text-slate-100">
                          {col.name}
                        </td>
                        <td className="py-2 px-3 font-mono-data text-[10px] text-primary-300">
                          {col.type}
                        </td>
                        <td className="py-2 px-3 whitespace-nowrap">
                          {col.isPrimaryKey && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 mr-1">
                              PK
                            </span>
                          )}
                          {col.isForeignKey && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-500/20 text-blue-300 mr-1">
                              FK
                            </span>
                          )}
                          {col.isPii && (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-500/20 text-rose-300">
                              <Lock className="w-2.5 h-2.5" />
                              <span>PII</span>
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-slate-400">
                          {col.description}
                          {col.references && (
                            <span className="text-[10px] text-blue-400 block mt-0.5">
                              → Liên kết {col.references}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-border-default/60 bg-surface-secondary/40">
          <span className="text-[11px] text-slate-400 italic">
            Nhấn phím <kbd className="px-1 py-0.5 bg-surface-secondary rounded font-mono text-slate-300">Esc</kbd> để đóng
          </span>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSelectTable}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white bg-primary-600 hover:bg-primary-500 shadow-sm transition-all active:scale-95"
            >
              <MessageSquarePlus className="w-3.5 h-3.5" />
              <span>Sử dụng bảng này trong câu hỏi</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-surface-secondary border border-border-default/60 transition-colors"
            >
              Đóng
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TableMetadataModal;
