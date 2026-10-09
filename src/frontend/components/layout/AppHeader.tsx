"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Search, HelpCircle, Bell } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function AppHeader() {
  const pathname = usePathname();
  const { t } = useLanguage();

  const getPageTitle = (path: string): string => {
    switch (path) {
      case "/workspace":
        return t("nav.workspace");
      case "/dashboard":
        return t("nav.dashboard");
      case "/saved-queries":
        return t("nav.savedQueries");
      case "/history":
        return t("nav.history");
      case "/data-sources":
        return t("nav.dataSources");
      case "/settings":
        return t("nav.settings");
      default:
        return t("nav.workspace");
    }
  };

  const currentTitle = getPageTitle(pathname);

  return (
    <header className="h-16 px-4 md:px-8 bg-surface/90 backdrop-blur-sm border-b border-line flex items-center justify-between gap-4 sticky top-0 z-10 shrink-0">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-muted text-xs">
        <span className="hover:text-foreground cursor-pointer transition-colors">
          QueryPilot
        </span>
        <span className="text-faint">›</span>
        <strong className="text-foreground font-bold">{currentTitle}</strong>
      </div>

      {/* Top Actions & Global Search */}
      <div className="flex items-center gap-2.5">
        <div className="hidden sm:flex items-center gap-2 border border-line rounded-lg bg-surface-2 px-2.5 h-8 text-xs text-muted w-48 md:w-56 focus-within:border-primary focus-within:bg-surface transition-colors shadow-sm">
          <Search className="w-3.5 h-3.5 shrink-0 text-faint" />
          <input
            type="text"
            placeholder={t("nav.searchPlaceholder")}
            className="w-full bg-transparent border-0 outline-none text-xs text-foreground placeholder:text-faint"
          />
          <kbd className="text-[10px] border border-line-strong rounded px-1 text-faint shrink-0 font-mono">
            ⌘K
          </kbd>
        </div>

        {/* Bilingual Quick Toggle */}
        <LanguageSwitcher />

        <button
          type="button"
          title={t("nav.help")}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-foreground hover:bg-surface-2 transition-colors border border-transparent hover:border-line"
        >
          <HelpCircle className="w-4 h-4" />
        </button>

        <button
          type="button"
          title={t("nav.notifications")}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-foreground hover:bg-surface-2 transition-colors border border-transparent hover:border-line"
        >
          <Bell className="w-4 h-4" />
        </button>

        <div className="w-[30px] h-[30px] rounded-full grid place-items-center bg-[#dcdcff] text-[#4242a9] text-[10px] font-bold shrink-0 ml-1">
          AL
        </div>
      </div>
    </header>
  );
}
