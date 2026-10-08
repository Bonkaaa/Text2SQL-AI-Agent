"use client";

import React from "react";
import { HelpCircle, Sparkles, CornerDownLeft } from "lucide-react";

export interface ClarificationCardProps {
  question?: string | null;
  options?: string[];
  onSelectOption: (option: string) => void;
  disabled?: boolean;
  className?: string;
}

const OPTION_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"];

/**
 * Tách nội dung phương án thành tiêu đề và mô tả giải thích (nếu có dấu hai chấm)
 */
function parseOptionContent(option: string): { title: string; description?: string } {
  const colonIndex = option.indexOf(":");
  if (colonIndex > 0 && colonIndex < option.length - 1) {
    return {
      title: option.slice(0, colonIndex).trim(),
      description: option.slice(colonIndex + 1).trim(),
    };
  }
  return { title: option };
}

export function ClarificationCard({
  question,
  options = [],
  onSelectOption,
  disabled = false,
  className = "",
}: ClarificationCardProps) {
  // Lắng nghe phím tắt bàn phím: A, B, C, D... hoặc 1, 2, 3, 4...
  const handleContainerKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (disabled || !options || options.length === 0) return;
    const key = e.key.toLowerCase();

    for (let idx = 0; idx < options.length; idx++) {
      const letter = (OPTION_LETTERS[idx] || "").toLowerCase();
      const num = String(idx + 1);

      if (key === letter || key === num) {
        e.preventDefault();
        onSelectOption(options[idx]);
        break;
      }
    }
  };

  const handleButtonKeyDown = (
    e: React.KeyboardEvent<HTMLButtonElement>,
    option: string
  ) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!disabled) {
        onSelectOption(option);
      }
    }
  };

  return (
    <div
      tabIndex={0}
      onKeyDown={handleContainerKeyDown}
      className={`rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 sm:p-5 space-y-4 backdrop-blur-md transition-all outline-none focus:ring-1 focus:ring-amber-500/40 ${className}`}
      role="region"
      aria-label="Thẻ làm rõ câu hỏi"
    >
      {/* Header Badge */}
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
          <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <span className="text-xs font-bold text-amber-300 tracking-wide uppercase">
          Cần làm rõ ý định câu hỏi (Interactive Decision)
        </span>
      </div>

      {/* Clarification Question Body */}
      {question && (
        <p className="text-sm font-medium text-slate-100 leading-relaxed">
          {question}
        </p>
      )}

      {/* Interactive Decision Cards Grid */}
      {options && options.length > 0 && (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1"
          role="group"
          aria-label="Các phương án làm rõ gợi ý"
        >
          {options.map((option, idx) => {
            const letter = OPTION_LETTERS[idx] || String(idx + 1);
            const { title, description } = parseOptionContent(option);

            return (
              <button
                key={idx}
                type="button"
                disabled={disabled}
                onClick={() => onSelectOption(option)}
                onKeyDown={(e) => handleButtonKeyDown(e, option)}
                className="group flex items-start gap-3 p-3 rounded-xl text-left text-xs font-medium text-slate-200 bg-surface-primary/80 hover:bg-amber-500/15 hover:text-white border border-amber-500/20 hover:border-amber-400/60 shadow-sm transition-all duration-200 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none focus:outline-none focus:ring-2 focus:ring-amber-400/40"
              >
                {/* Shortcut Letter Badge */}
                <span className="w-5 h-5 rounded-md bg-amber-500/20 text-amber-300 font-bold text-[11px] font-mono-data flex items-center justify-center flex-shrink-0 border border-amber-500/30 group-hover:bg-amber-400 group-hover:text-black transition-colors mt-0.5">
                  {letter}
                </span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="text-slate-100 font-semibold group-hover:text-amber-200 transition-colors">
                    {title}
                  </div>
                  {description && (
                    <div className="text-[11px] text-slate-400 mt-0.5 leading-snug group-hover:text-slate-300">
                      {description}
                    </div>
                  )}
                </div>

                <CornerDownLeft className="w-3.5 h-3.5 text-slate-500 opacity-0 group-hover:opacity-100 text-amber-400 transition-opacity mt-1 shrink-0" />
              </button>
            );
          })}
        </div>
      )}

      {/* Guidance Footer */}
      <div className="pt-1 text-[11px] text-amber-300/70 italic flex items-center gap-1.5 flex-wrap">
        <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
        <span>
          Gợi ý: Bấm phím ký tự hoặc số trên bàn phím để chọn nhanh, hoặc gõ câu trả lời trực tiếp vào ô chat.
        </span>
      </div>
    </div>
  );
}

export default ClarificationCard;
