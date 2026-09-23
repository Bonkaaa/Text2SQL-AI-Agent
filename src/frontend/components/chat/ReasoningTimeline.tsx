"use client";

import React, { useState } from "react";
import {
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
} from "lucide-react";

import { formatDurationSeconds } from "@/utils/formatters";

export interface ReasoningStep {
  id: string;
  stepNumber: number;
  title: string;
  description: string;
}

export const DEFAULT_REASONING_STEPS: ReasoningStep[] = [
  {
    id: "intent",
    stepNumber: 1,
    title: "1. Làm rõ ý định:",
    description: "Xác định câu hỏi không mơ hồ, ngữ cảnh phân tích hợp lệ.",
  },
  {
    id: "retriever",
    stepNumber: 2,
    title: "2. Schema & Categorical Retriever:",
    description: "Lấy ngữ cảnh bảng liên quan trong 8 bảng TPC-H.",
  },
  {
    id: "generator",
    stepNumber: 3,
    title: "3. SQL Generator:",
    description: "Tạo câu truy vấn chuẩn ANSI SQL và tương thích DuckDB.",
  },
  {
    id: "control-synthesizer",
    stepNumber: 4,
    title: "4. LangGraph Control Guard & Synthesizer:",
    description: "AST Sanitizer kiểm tra an toàn (chỉ cho phép SELECT), RBAC & tổng hợp dữ liệu.",
  },
];

export interface ReasoningTimelineProps {
  isLoading?: boolean;
  currentStep?: number;
  executionTimeMs?: number;
  steps?: ReasoningStep[];
  defaultExpanded?: boolean;
  className?: string;
}

export function ReasoningTimeline({
  isLoading = false,
  currentStep = 1,
  executionTimeMs,
  steps = DEFAULT_REASONING_STEPS,
  defaultExpanded = false,
  className = "",
}: ReasoningTimelineProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  // Nếu đang loading thì tự động mở rộng để hiển thị trực quan tiến trình
  const expanded = isLoading || isOpen;

  const toggleExpand = () => {
    setIsOpen((prev) => !prev);
  };

  return (
    <div
      className={`rounded-xl border border-surface-border bg-surface-subtle/30 overflow-hidden transition-all duration-200 ${className}`}
    >
      {/* Header Accordion Bar */}
      <button
        type="button"
        onClick={toggleExpand}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-surface-subtle/50 transition-colors select-none focus:outline-none focus:ring-1 focus:ring-brand-500/30"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2">
          {isLoading ? (
            <BrainCircuit className="w-3.5 h-3.5 text-brand-400 animate-spin" />
          ) : (
            <BrainCircuit className="w-3.5 h-3.5 text-brand-400" />
          )}
          <span className="font-semibold text-slate-200">
            Quy trình suy luận (DeepAgents CoT)
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          {executionTimeMs !== undefined && (
            <span className="flex items-center gap-1 text-[11px] text-slate-400 font-mono bg-white/5 px-2 py-0.5 rounded-full border border-white/5">
              <Clock className="w-3 h-3 text-brand-400" />
              <span>{formatDurationSeconds(executionTimeMs)}</span>
            </span>
          )}

          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 transition-transform duration-200" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-slate-400 transition-transform duration-200" />
          )}
        </div>
      </button>

      {/* Expanded Steps List */}
      {expanded && (
        <div className="p-3 border-t border-surface-border space-y-2.5 text-xs text-slate-300 animate-in fade-in duration-150">
          {steps.map((step) => {
            const isCompleted = !isLoading || step.stepNumber < currentStep;
            const isActive = isLoading && step.stepNumber === currentStep;
            const isPending = isLoading && step.stepNumber > currentStep;

            return (
              <div
                key={step.id}
                className="flex items-start gap-2.5"
                data-testid={
                  isActive
                    ? `step-active-${step.stepNumber}`
                    : isCompleted
                    ? `step-done-${step.stepNumber}`
                    : `step-pending-${step.stepNumber}`
                }
              >
                {/* Step Indicator Icon */}
                <div className="mt-0.5 flex-shrink-0">
                  {isActive ? (
                    <Loader2 className="w-3.5 h-3.5 text-brand-400 animate-spin" />
                  ) : isCompleted ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <span className="inline-block w-2 h-2 rounded-full bg-slate-600 ml-1 mt-1" />
                  )}
                </div>

                {/* Step Content */}
                <div className="leading-relaxed">
                  <span
                    className={`font-semibold mr-1.5 ${
                      isActive
                        ? "text-brand-300"
                        : isCompleted
                        ? "text-slate-200"
                        : "text-slate-500"
                    }`}
                  >
                    {step.title}
                  </span>
                  <span
                    className={
                      isActive
                        ? "text-slate-300"
                        : isCompleted
                        ? "text-slate-400"
                        : "text-slate-600"
                    }
                  >
                    {step.description}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ReasoningTimeline;
