"use client";

import React from "react";
import { useLanguage } from "@/context/LanguageContext";

export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { locale, toggleLocale } = useLanguage();

  return (
    <button
      type="button"
      onClick={toggleLocale}
      aria-label={locale === "vi" ? "Chuyển sang English" : "Switch to Tiếng Việt"}
      title={locale === "vi" ? "Chuyển sang English" : "Chuyển sang Tiếng Việt"}
      className={`flex items-center gap-1.5 px-2.5 h-8 rounded-lg border border-line bg-surface-2 hover:bg-surface text-xs font-bold text-foreground transition-all shadow-xs hover:border-primary/40 ${className}`}
    >
      <span className="text-sm select-none" aria-hidden="true">
        {locale === "vi" ? "🇻🇳" : "🇬🇧"}
      </span>
      <span className="text-[11px] font-extrabold uppercase tracking-wide">
        {locale === "vi" ? "VI" : "EN"}
      </span>
    </button>
  );
}
