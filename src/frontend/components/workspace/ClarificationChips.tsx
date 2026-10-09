"use client";

import React from "react";
import { HelpCircle, ArrowRight } from "lucide-react";

interface ClarificationChipsProps {
  question: string;
  options: string[];
  onSelectOption: (option: string) => void;
}

export function ClarificationChips({
  question,
  options,
  onSelectOption,
}: ClarificationChipsProps) {
  if (!options || options.length === 0) return null;

  return (
    <div className="bg-primary-soft/60 border border-primary/25 rounded-xl p-3 space-y-2 mt-2">
      <div className="flex items-center gap-1.5 text-xs font-bold text-primary">
        <HelpCircle className="w-3.5 h-3.5" />
        <span>{question}</span>
      </div>

      <div className="flex flex-wrap gap-1.5 pt-1">
        {options.map((opt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectOption(opt)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface hover:bg-surface-2 text-foreground border border-line-strong hover:border-primary hover:text-primary transition shadow-sm text-left"
          >
            <span>{opt}</span>
            <ArrowRight className="w-3 h-3 text-faint group-hover:text-primary" />
          </button>
        ))}
      </div>
    </div>
  );
}
