"use client";

import React from "react";
import { HelpCircle, Sparkles } from "lucide-react";

export interface ClarificationCardProps {
  question?: string | null;
  options?: string[];
  onSelectOption: (option: string) => void;
  disabled?: boolean;
  className?: string;
}

const OPTION_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"];

export function ClarificationCard({
  question,
  options = [],
  onSelectOption,
  disabled = false,
  className = "",
}: ClarificationCardProps) {
  const handleKeyDown = (
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
      className={`rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 sm:p-5 space-y-3.5 backdrop-blur-md transition-all ${className}`}
      role="region"
      aria-label="Thẻ làm rõ câu hỏi"
    >
      {/* Header Badge */}
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
          <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <span className="text-xs font-bold text-amber-300 tracking-wide uppercase">
          Cần làm rõ ý định câu hỏi
        </span>
      </div>

      {/* Clarification Question Body */}
      {question && (
        <p className="text-sm font-medium text-slate-100 leading-relaxed">
          {question}
        </p>
      )}

      {/* Suggested Option Chips */}
      {options && options.length > 0 && (
        <div
          className="flex flex-wrap gap-2 pt-1"
          role="group"
          aria-label="Các phương án làm rõ gợi ý"
        >
          {options.map((option, idx) => {
            const letter = OPTION_LETTERS[idx] || String(idx + 1);

            return (
              <button
                key={idx}
                type="button"
                disabled={disabled}
                onClick={() => onSelectOption(option)}
                onKeyDown={(e) => handleKeyDown(e, option)}
                className="group flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-200 bg-[#171922]/90 hover:bg-amber-500/20 hover:text-white border border-amber-500/25 hover:border-amber-400/60 shadow-sm transition-all duration-200 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none focus:outline-none focus:ring-2 focus:ring-amber-400/40"
              >
                <span className="w-4 h-4 rounded-md bg-amber-500/20 text-amber-300 font-bold text-[10px] flex items-center justify-center flex-shrink-0 border border-amber-500/30 group-hover:bg-amber-400 group-hover:text-black transition-colors">
                  {letter}
                </span>
                <span>{option}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Guidance Footer */}
      <div className="pt-1 text-[11px] text-amber-300/70 italic flex items-center gap-1.5">
        <Sparkles className="w-3 h-3 text-amber-400 flex-shrink-0" />
        <span>
          Nhấn vào một trong các lựa chọn trên để tiếp tục, hoặc gõ câu trả lời trực tiếp vào ô chat.
        </span>
      </div>
    </div>
  );
}

export default ClarificationCard;
