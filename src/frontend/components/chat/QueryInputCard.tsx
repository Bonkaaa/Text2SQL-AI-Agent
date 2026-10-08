"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ArrowUp,
  Database,
  Loader2,
  Table2,
  X,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";
import { TPCDS_DOMAINS } from "@/data/tpcdsCatalog";

export interface QueryInputCardProps {
  onSubmit?: (prompt: string) => void;
  onSendMessage?: (text: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  initialValue?: string;
  placeholder?: string;
  className?: string;
}

export function QueryInputCard({
  onSubmit,
  onSendMessage,
  isLoading = false,
  disabled = false,
  initialValue = "",
  placeholder = "Ask Text2SQL...",
  className = "",
}: QueryInputCardProps) {
  const [prompt, setPrompt] = useState(initialValue);
  const [isMentionOpen, setIsMentionOpen] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { showToast } = useAppContext();

  const isInputDisabled = isLoading || disabled;

  // Auto focus and set initial value
  useEffect(() => {
    if (initialValue) {
      setPrompt(initialValue);
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.style.height = `${Math.min(
          textareaRef.current.scrollHeight,
          120
        )}px`;
        textareaRef.current.focus();
      }
    }
  }, [initialValue]);

  // Global shortcut Ctrl+K / Cmd+K to focus textarea
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setPrompt(val);

    // Native auto-resize height (Ponytail ladder: native DOM, zero dependencies)
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;

    // Trigger @ table mention if typing @
    const lastChar = val.slice(-1);
    if (lastChar === "@") {
      setIsMentionOpen(true);
      setMentionFilter("");
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || isInputDisabled) return;

    if (onSubmit) {
      onSubmit(trimmed);
    } else if (onSendMessage) {
      onSendMessage(trimmed);
    }

    setPrompt("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    setIsMentionOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter without Shift triggers submit
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    // Escape closes mention menu
    if (e.key === "Escape" && isMentionOpen) {
      setIsMentionOpen(false);
    }
  };

  const handleInsertTable = (tableName: string) => {
    let newPrompt = prompt;
    if (newPrompt.endsWith("@")) {
      newPrompt = `${newPrompt}${tableName} `;
    } else {
      newPrompt = newPrompt ? `${newPrompt} @${tableName} ` : `@${tableName} `;
    }

    setPrompt(newPrompt);
    setIsMentionOpen(false);
    showToast(`Đã thêm @${tableName} vào câu lệnh`, "info", 1200);

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.style.height = "auto";
        textareaRef.current.style.height = `${Math.min(
          textareaRef.current.scrollHeight,
          120
        )}px`;
      }
    }, 50);
  };

  // Flatten and filter 24 TPC-DS tables
  const allTables = TPCDS_DOMAINS.flatMap((d) => d.tables);
  const filteredTables = mentionFilter
    ? allTables.filter(
        (t) =>
          t.name.toLowerCase().includes(mentionFilter.toLowerCase()) ||
          t.label.toLowerCase().includes(mentionFilter.toLowerCase())
      )
    : allTables;

  return (
    <div className={`w-full relative ${className}`}>
      {/* Popover: 24 TPC-DS Tables Selector (Nổi bên trên thanh Capsule) */}
      {isMentionOpen && (
        <div className="absolute left-0 right-0 bottom-full mb-3 p-3 rounded-2xl bg-white dark:bg-[#0c1322]/98 border border-slate-200 dark:border-surface-border shadow-2xl backdrop-blur-xl z-50 animate-in fade-in slide-in-from-bottom-2 duration-150 max-h-64 overflow-y-auto custom-scrollbar">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-surface-border/60 px-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200">
              <Table2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>Bảng dữ liệu TPC-DS (24 bảng)</span>
            </div>
            <button
              type="button"
              onClick={() => setIsMentionOpen(false)}
              className="p-1 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-surface-secondary/50 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
            {filteredTables.map((table) => (
              <button
                key={table.name}
                type="button"
                onClick={() => handleInsertTable(table.name)}
                className="flex flex-col items-start p-2 rounded-xl hover:bg-blue-50 dark:hover:bg-brand-500/10 border border-transparent hover:border-blue-200 dark:hover:border-brand-500/30 text-left transition-colors"
              >
                <span className="text-[11px] font-mono text-blue-600 dark:text-blue-300 font-semibold truncate w-full">
                  {table.name}
                </span>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate w-full">
                  {table.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Single-line Floating Capsule Bar (Google Gemini Style) */}
      <form
        onSubmit={handleSubmit}
        className="relative flex items-center gap-2 bg-white/95 dark:bg-[#0c1322]/95 border border-slate-300 dark:border-surface-border/80 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/20 rounded-full px-3 py-1.5 shadow-xl dark:shadow-2xl backdrop-blur-xl transition-all duration-200"
      >
        {/* Left: @ TPC-DS Mention Pill Button */}
        <button
          type="button"
          onClick={() => setIsMentionOpen(!isMentionOpen)}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all flex-shrink-0 ${
            isMentionOpen
              ? "bg-blue-100 dark:bg-brand-600/30 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-brand-500/50 shadow-sm"
              : "bg-slate-100 dark:bg-surface-secondary/80 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-surface-border/80 hover:bg-slate-200 dark:hover:bg-surface-tertiary hover:text-slate-900 dark:hover:text-white"
          }`}
          title="Chọn bảng TPC-DS (@-mention)"
          aria-label="Bảng TPC-DS"
        >
          <Database className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
          <span className="hidden sm:inline">Bảng TPC-DS</span>
        </button>

        {/* Center: Textarea Auto-Expanding on same line */}
        <div className="flex-1 flex items-center min-w-0">
          <textarea
            ref={textareaRef}
            rows={1}
            value={prompt}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            disabled={isInputDisabled}
            placeholder={placeholder}
            className="w-full bg-transparent text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 outline-none resize-none min-h-[32px] max-h-[120px] custom-scrollbar px-1 py-1 font-sans-ui leading-relaxed"
          />
        </div>

        {/* Right: Submit Button Pill */}
        <button
          type="submit"
          disabled={isInputDisabled || !prompt.trim()}
          title="Gửi câu hỏi"
          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-transform active:scale-95 ${
            prompt.trim() && !isInputDisabled
              ? "bg-brand-600 text-white hover:bg-brand-500 shadow-md shadow-brand-500/20"
              : "bg-slate-100 dark:bg-surface-tertiary text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-200 dark:border-transparent"
          }`}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-white" />
          ) : (
            <ArrowUp className="w-4 h-4" />
          )}
        </button>
      </form>
    </div>
  );
}

export const ChatInput = QueryInputCard;
export default QueryInputCard;

