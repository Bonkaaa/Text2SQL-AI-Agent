"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ArrowUp,
  ChevronDown,
  Mic,
  Plus,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";

interface QueryInputCardProps {
  onSubmit: (prompt: string) => void;
  isLoading?: boolean;
  initialValue?: string;
}

export function QueryInputCard({
  onSubmit,
  isLoading = false,
  initialValue = "",
}: QueryInputCardProps) {
  const [prompt, setPrompt] = useState(initialValue);
  const [selectedModel, setSelectedModel] = useState<"TPC-H" | "Flash">("TPC-H");
  const [isModelDropdownOpen, setModelDropdownOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useAppContext();

  useEffect(() => {
    if (initialValue) {
      setPrompt(initialValue);
      inputRef.current?.focus();
    }
  }, [initialValue]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || isLoading) return;

    onSubmit(trimmed);
    setPrompt("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto px-4">
      {/* Pill Chatbox Container matching Image 3 */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 bg-[#171922] hover:bg-[#1b1e2a] focus-within:bg-[#1b1e2a] focus-within:ring-1 focus-within:ring-white/20 border border-white/10 rounded-full px-4 py-2.5 shadow-card transition-all duration-200"
      >
        {/* Left: Plus (+) Attachment Icon */}
        <button
          type="button"
          onClick={() => showToast("Đính kèm tệp dữ liệu hoặc ngữ cảnh", "info", 1800)}
          className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors flex-shrink-0"
          title="Đính kèm tệp"
        >
          <Plus className="w-4 h-4" />
        </button>

        {/* Center: Text Input */}
        <input
          ref={inputRef}
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="Ask Text2SQL..."
          className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-400 outline-none px-1"
        />

        {/* Right: Model Selector & Mic/Send Button */}
        <div className="flex items-center gap-1.5 flex-shrink-0 relative">
          {/* Model Tag Dropdown (like 'Flash ⌄' in Image 3) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setModelDropdownOpen(!isModelDropdownOpen)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            >
              <span>{selectedModel}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {isModelDropdownOpen && (
              <div className="absolute right-0 bottom-full mb-2 w-32 p-1 rounded-xl bg-[#1e2230] border border-white/10 shadow-card z-50 animate-in fade-in zoom-in-95 duration-150">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedModel("TPC-H");
                    setModelDropdownOpen(false);
                    showToast("Đã chọn mô hình: TPC-H DeepAgents", "info", 1500);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                    selectedModel === "TPC-H"
                      ? "bg-brand-500/20 text-brand-300 font-semibold"
                      : "text-slate-300 hover:bg-white/5"
                  }`}
                >
                  TPC-H
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedModel("Flash");
                    setModelDropdownOpen(false);
                    showToast("Đã chọn mô hình: Flash Fast Engine", "info", 1500);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                    selectedModel === "Flash"
                      ? "bg-brand-500/20 text-brand-300 font-semibold"
                      : "text-slate-300 hover:bg-white/5"
                  }`}
                >
                  Flash
                </button>
              </div>
            )}
          </div>

          {/* Mic / Send Action Icon */}
          <button
            type={prompt.trim() ? "submit" : "button"}
            onClick={prompt.trim() ? handleSubmit : () => showToast("Nhập liệu bằng giọng nói (Voice input)", "info", 1800)}
            disabled={isLoading}
            className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors flex items-center justify-center"
            title={prompt.trim() ? "Gửi câu hỏi" : "Giọng nói"}
          >
            {isLoading ? (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : prompt.trim() ? (
              <ArrowUp className="w-4 h-4 text-brand-400" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
