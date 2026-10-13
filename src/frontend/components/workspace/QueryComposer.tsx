import React, { useState, useRef, KeyboardEvent } from "react";
import { Send, Database, Loader2 } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";

interface QueryComposerProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

export function QueryComposer({
  onSubmit,
  isLoading,
  placeholder,
}: QueryComposerProps) {
  const { t } = useLanguage();
  const effectivePlaceholder =
    placeholder ||
    t(
      "workspace.composerPlaceholder",
      "Ask a question about your data (e.g., Top 5 customers by revenue in ASIA in 1995?)..."
    );
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSubmit(input.trim());
        setInput("");
      }
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSubmit(input.trim());
      setInput("");
    }
  };

  return (
    <div className="p-3 border-t border-line bg-surface">
      <form
        onSubmit={handleFormSubmit}
        className="border border-line-strong rounded-xl p-2.5 bg-surface focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition shadow-card"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={2}
          placeholder={effectivePlaceholder}
          aria-label="Ask a question about your data"
          className="w-full bg-transparent border-0 outline-none resize-none text-xs text-foreground placeholder:text-faint leading-relaxed disabled:opacity-50"
        />

        <div className="flex items-center justify-between gap-2 pt-2 border-t border-line/60">
          <div className="flex items-center gap-2 text-[10px] text-muted">
            <span className="inline-flex items-center gap-1 font-semibold">
              <Database className="w-3 h-3 text-primary" />
              TPC-H Analytics · DuckDB
            </span>
            <span>·</span>
            <span className="text-faint">{t("workspace.enterToSend")}</span>
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            aria-label="Send query"
            className="w-7 h-7 rounded-lg bg-primary hover:bg-primary-strong text-white grid place-items-center transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </form>

      <div className="text-[9px] text-faint mt-1.5 px-1">
        {t("workspace.aiDisclaimer")}
      </div>
    </div>
  );
}
