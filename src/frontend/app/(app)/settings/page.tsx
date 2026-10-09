"use client";

import React, { useState } from "react";
import {
  Settings,
  Shield,
  Sliders,
  User,
  Check,
  RotateCcw,
  AlertTriangle,
  Layers,
  Globe,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useSettings } from "@/hooks/useSettings";
import { useLanguage } from "@/context/LanguageContext";

export default function SettingsPage() {
  const { user } = useAuth();
  const { settings, updateSettings, resetSettings } = useSettings();
  const { t, locale, setLocale } = useLanguage();

  const [saved, setSaved] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleResetData = () => {
    resetSettings();
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem("querypilot_settings");
        localStorage.removeItem("querypilot_query_history");
        localStorage.removeItem("querypilot_saved_queries");
      } catch {
        // Ignore
      }
    }
    setResetMessage("Data & Cache Reset Successfully! Session telemetry restored to defaults.");
    setTimeout(() => setResetMessage(null), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Heading */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <div className="text-primary text-[10px] font-extrabold uppercase tracking-widest mb-1.5">
            Preferences & Controls
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            Workspace Settings
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1 max-w-2xl leading-relaxed">
            Manage your analyst profile, query safety defaults, row limits, and developer telemetry modes.
          </p>
        </div>

        <button
          type="button"
          onClick={handleSave}
          className="inline-flex items-center gap-2 bg-primary hover:bg-primary-strong text-white px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-sm"
        >
          {saved ? <Check className="w-4 h-4 text-emerald" /> : <Settings className="w-4 h-4" />}
          {saved ? "Changes saved" : "Save changes"}
        </button>
      </div>

      {resetMessage && (
        <div className="p-3 rounded-lg bg-emerald-soft border border-emerald/30 text-emerald text-xs font-semibold flex items-center gap-2 transition-all">
          <Check className="w-4 h-4 shrink-0" />
          <span>{resetMessage}</span>
        </div>
      )}

      <div className="space-y-5">
        {/* Profile Section */}
        <section className="bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-foreground font-bold text-sm">
              <User className="w-4 h-4 text-primary" />
              <h3>Analyst Profile</h3>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-primary-soft text-primary uppercase tracking-wider">
              {user.role}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label htmlFor="user-display-name" className="text-muted text-[11px] font-bold block mb-1">
                Display Name
              </label>
              <input
                id="user-display-name"
                type="text"
                defaultValue={user.name}
                className="w-full bg-surface-2 border border-line rounded-lg px-3 py-2 text-foreground text-xs outline-none focus:border-primary font-medium"
              />
            </div>
            <div>
              <label htmlFor="user-email-address" className="text-muted text-[11px] font-bold block mb-1">
                Email Address
              </label>
              <input
                id="user-email-address"
                type="email"
                defaultValue={user.email}
                className="w-full bg-surface-2 border border-line rounded-lg px-3 py-2 text-foreground text-xs outline-none focus:border-primary font-medium"
              />
            </div>
          </div>
        </section>

        {/* Safety & Query Execution Section */}
        <section className="bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-4">
          <div className="flex items-center gap-2 text-foreground font-bold text-sm">
            <Shield className="w-4 h-4 text-emerald" />
            <h3>Query Governance & Safety Defaults</h3>
          </div>

          <div className="divide-y divide-line text-xs">
            {/* Strict Read-Only Mode */}
            <div className="flex items-center justify-between py-3">
              <div>
                <strong className="text-foreground block">Strict Read-Only SELECT Mode</strong>
                <span className="text-muted text-[11px]">
                  Automatically block INSERT, UPDATE, DELETE, DROP and any mutation statements via AST.
                </span>
              </div>
              <button
                type="button"
                role="switch"
                aria-label="Strict Read-Only SELECT Mode"
                aria-checked={settings.readOnly}
                onClick={() => updateSettings({ readOnly: !settings.readOnly })}
                className={`w-10 h-6 rounded-full transition-colors relative p-0.5 ${
                  settings.readOnly ? "bg-primary" : "bg-line-strong"
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${
                    settings.readOnly ? "translate-x-4" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            {/* Require HITL Review */}
            <div className="flex items-center justify-between py-3">
              <div>
                <strong className="text-foreground block">Require HITL Review for Large Queries</strong>
                <span className="text-muted text-[11px]">
                  Pause execution and prompt for administrator approval when estimated cost exceeds budget.
                </span>
              </div>
              <button
                type="button"
                role="switch"
                aria-label="Require HITL Review for Large Queries"
                aria-checked={settings.requireHitlApproval}
                onClick={() =>
                  updateSettings({ requireHitlApproval: !settings.requireHitlApproval })
                }
                className={`w-10 h-6 rounded-full transition-colors relative p-0.5 ${
                  settings.requireHitlApproval ? "bg-primary" : "bg-line-strong"
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${
                    settings.requireHitlApproval ? "translate-x-4" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            {/* Row Limit Dropdown */}
            <div className="flex items-center justify-between py-3">
              <div>
                <strong className="text-foreground block">Default Row Limit</strong>
                <span className="text-muted text-[11px]">
                  Maximum number of rows returned by exploratory analytical queries.
                </span>
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="default-row-limit-select" className="sr-only">
                  Default Row Limit
                </label>
                <select
                  id="default-row-limit-select"
                  aria-label="Default Row Limit"
                  value={settings.defaultRowLimit}
                  onChange={(e) =>
                    updateSettings({ defaultRowLimit: Number(e.target.value) })
                  }
                  className="bg-surface-2 border border-line text-foreground text-xs font-bold rounded-lg px-2.5 py-1.5 outline-none focus:border-primary cursor-pointer"
                >
                  <option value="50">50 rows</option>
                  <option value="100">100 rows</option>
                  <option value="250">250 rows</option>
                  <option value="500">500 rows</option>
                </select>
              </div>
            </div>
          </div>
        </section>

        {/* Language & Localization Section */}
        <section className="bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-4">
          <div className="flex items-center gap-2 text-foreground font-bold text-sm">
            <Globe className="w-4 h-4 text-primary" />
            <h3>{t("settings.languageTitle")}</h3>
          </div>
          <p className="text-muted text-xs leading-relaxed">
            {t("settings.languageDesc")}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <button
              type="button"
              onClick={() => setLocale("vi")}
              className={`flex items-center justify-between p-3 rounded-lg border text-xs font-bold transition-all text-left ${
                locale === "vi"
                  ? "border-primary bg-primary-soft/40 text-foreground shadow-xs ring-1 ring-primary"
                  : "border-line bg-surface-2 hover:bg-surface text-muted"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🇻🇳</span>
                <div>
                  <div className="font-bold text-foreground">Tiếng Việt</div>
                  <div className="text-[10px] text-muted font-normal">Vietnamese</div>
                </div>
              </div>
              {locale === "vi" && <Check className="w-4 h-4 text-primary shrink-0" />}
            </button>

            <button
              type="button"
              onClick={() => setLocale("en")}
              className={`flex items-center justify-between p-3 rounded-lg border text-xs font-bold transition-all text-left ${
                locale === "en"
                  ? "border-primary bg-primary-soft/40 text-foreground shadow-xs ring-1 ring-primary"
                  : "border-line bg-surface-2 hover:bg-surface text-muted"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🇬🇧</span>
                <div>
                  <div className="font-bold text-foreground">English</div>
                  <div className="text-[10px] text-muted font-normal">Tiếng Anh</div>
                </div>
              </div>
              {locale === "en" && <Check className="w-4 h-4 text-primary shrink-0" />}
            </button>
          </div>
        </section>

        {/* Developer Telemetry Section */}
        <section className="bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-4">
          <div className="flex items-center gap-2 text-foreground font-bold text-sm">
            <Sliders className="w-4 h-4 text-primary" />
            <h3>Developer Mode & Execution Trace</h3>
          </div>

          <div className="divide-y divide-line text-xs">
            <div className="flex items-center justify-between py-2">
              <div>
                <strong className="text-foreground block">
                  Show Agent Execution Trace in Workspace
                </strong>
                <span className="text-muted text-[11px]">
                  Expose latency breakdowns, schema match tokens, and subagent invocation steps.
                </span>
              </div>
              <button
                type="button"
                role="switch"
                aria-label="Show Agent Execution Trace in Workspace"
                aria-checked={settings.showTrace}
                onClick={() => updateSettings({ showTrace: !settings.showTrace })}
                className={`w-10 h-6 rounded-full transition-colors relative p-0.5 ${
                  settings.showTrace ? "bg-primary" : "bg-line-strong"
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${
                    settings.showTrace ? "translate-x-4" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>
        </section>

        {/* Maintenance & Demo Data Section */}
        <section className="bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-3">
          <div className="flex items-center gap-2 text-foreground font-bold text-sm">
            <Layers className="w-4 h-4 text-amber" />
            <h3>Data Cache & Diagnostics</h3>
          </div>
          <p className="text-muted text-xs leading-relaxed">
            Clear stored local browser cache, reset preset queries, and restore initial configuration state.
          </p>

          <div className="pt-2">
            <button
              type="button"
              onClick={handleResetData}
              className="inline-flex items-center gap-2 bg-surface-2 hover:bg-red-50 text-foreground hover:text-red-600 border border-line hover:border-red-200 px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-xs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Demo Data / Clear Cache
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
