"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  Sparkles,
  LayoutGrid,
  Bookmark,
  History,
  Database,
  Settings,
  HelpCircle,
  MoreHorizontal,
  Layers,
} from "lucide-react";
import { DatabaseSwitcher } from "./DatabaseSwitcher";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/context/LanguageContext";

export function AppSidebar() {
  const pathname = usePathname();
  const { t } = useLanguage();

  const workspaceNavItems = [
    { name: t("nav.workspace"), href: "/workspace", icon: Sparkles },
    { name: t("nav.dashboard"), href: "/dashboard", icon: LayoutGrid },
    { name: t("nav.savedQueries"), href: "/saved-queries", icon: Bookmark, tag: "3" },
    { name: t("nav.history"), href: "/history", icon: History },
  ];

  const dataNavItems = [
    { name: t("nav.dataSources"), href: "/data-sources", icon: Database },
    { name: t("nav.settings"), href: "/settings", icon: Settings },
  ];

  return (
    <aside className="sticky top-0 h-screen flex flex-col p-3 md:p-3.5 bg-surface border-r border-line z-20 w-[66px] md:w-[238px] transition-all duration-200 shrink-0">
      {/* Brand Header */}
      <div className="flex items-center gap-2.5 px-1.5 md:px-2.5 py-2 md:pb-5">
        <div className="w-[34px] h-[34px] rounded-[11px] grid place-items-center text-white bg-gradient-to-br from-[#7777f5] to-[#4b4bc5] shadow-[0_5px_14px_rgba(82,82,210,0.23)] shrink-0">
          <Layers className="w-5 h-5" />
        </div>
        <div className="hidden md:block leading-none">
          <div className="text-[15px] font-bold tracking-tight text-foreground">
            QueryPilot
          </div>
          <div className="text-[10px] text-muted tracking-wider uppercase font-semibold mt-1">
            AI data workspace
          </div>
        </div>
      </div>

      {/* Database Switcher Widget */}
      <div className="hidden md:block mt-1">
        <DatabaseSwitcher />
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto space-y-4 pt-2">
        <div>
          <div className="hidden md:block text-faint text-[10px] tracking-wider font-bold uppercase px-3 pb-2">
            {t("nav.workspace")}
          </div>
          <nav className="grid gap-1" aria-label="Workspace navigation">
            {workspaceNavItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-2.5 md:px-3 py-2.5 rounded-lg text-xs font-semibold transition-colors duration-150 justify-center md:justify-start",
                    isActive
                      ? "bg-primary-soft text-primary font-bold shadow-sm"
                      : "text-muted hover:bg-surface-2 hover:text-foreground"
                  )}
                  title={item.name}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="hidden md:inline truncate">{item.name}</span>
                  {item.tag && (
                    <span className="hidden md:inline-block ml-auto rounded bg-emerald-soft text-emerald text-[9px] px-1.5 py-0.5 font-bold">
                      {item.tag}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        <div>
          <div className="hidden md:block text-faint text-[10px] tracking-wider font-bold uppercase px-3 pb-2 pt-2">
            Data
          </div>
          <nav className="grid gap-1" aria-label="Data navigation">
            {dataNavItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-2.5 md:px-3 py-2.5 rounded-lg text-xs font-semibold transition-colors duration-150 justify-center md:justify-start",
                    isActive
                      ? "bg-primary-soft text-primary font-bold shadow-sm"
                      : "text-muted hover:bg-surface-2 hover:text-foreground"
                  )}
                  title={item.name}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="hidden md:inline truncate">{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Help Card (Desktop only) */}
      <div className="hidden md:block bg-surface-2 border border-line rounded-xl p-3 my-3">
        <div className="w-7 h-7 rounded-lg bg-primary-soft text-primary grid place-items-center mb-2">
          <HelpCircle className="w-4 h-4" />
        </div>
        <strong className="text-[11px] block font-bold text-foreground">
          {t("nav.helpCardTitle")}
        </strong>
        <p className="text-muted text-[10px] leading-relaxed my-1.5">
          {t("nav.helpCardDesc")}
        </p>
        <Link
          href="/data-sources"
          className="text-primary text-[10px] font-bold hover:underline inline-flex items-center gap-1"
        >
          {t("nav.docs")} →
        </Link>
      </div>

      {/* Profile Section */}
      <SidebarProfile />
    </aside>
  );
}

function SidebarProfile() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [profileOpen, setProfileOpen] = useState(false);

  const initials = user.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .substring(0, 2)
    .toUpperCase();

  const handleSignOut = () => {
    logout();
    setProfileOpen(false);
    router.push("/login");
  };

  return (
    <div className="relative border-t border-line pt-3 flex items-center gap-2 justify-center md:justify-start">
      <div className="w-[31px] h-[31px] rounded-full grid place-items-center bg-[#dcdcff] text-[#4242a9] text-[10px] font-bold shrink-0">
        {initials}
      </div>
      <div className="hidden md:block leading-tight min-w-0 flex-1">
        <div className="text-[11px] font-bold text-foreground truncate">
          {user.name}
        </div>
        <div className="text-[10px] text-muted truncate">
          Role: {user.role}
        </div>
      </div>
      <button
        type="button"
        onClick={() => setProfileOpen(!profileOpen)}
        className="hidden md:block text-muted hover:text-foreground p-1 rounded hover:bg-surface-2 transition-colors ml-auto"
        aria-label="User account menu"
      >
        <MoreHorizontal className="w-4 h-4" />
      </button>

      {/* Profile Dropdown */}
      {profileOpen && (
        <div className="absolute bottom-12 left-0 w-48 bg-surface border border-line rounded-lg shadow-panel p-1.5 z-30 animate-in fade-in zoom-in-95 duration-150">
          <div className="px-2.5 py-1.5 border-b border-line mb-1">
            <div className="text-[11px] font-bold truncate">{user.email}</div>
            <div className="text-[9px] text-muted">Role: {user.role}</div>
          </div>
          <Link
            href="/settings"
            onClick={() => setProfileOpen(false)}
            className="w-full text-left px-2.5 py-1.5 text-xs rounded hover:bg-surface-2 text-foreground block"
          >
            Preferences
          </Link>
          <button
            type="button"
            onClick={handleSignOut}
            className="w-full text-left px-2.5 py-1.5 text-xs rounded hover:bg-surface-2 text-rose"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
