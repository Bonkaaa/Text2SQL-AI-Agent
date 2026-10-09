"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  ShieldCheck,
  Database,
  ArrowRight,
  User,
  Shield,
  Check,
} from "lucide-react";
import { useAuth, PersonaType, PRESET_PERSONAS } from "@/context/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [selectedPersona, setSelectedPersona] = useState<PersonaType>("analyst");
  const [email, setEmail] = useState(PRESET_PERSONAS.analyst.email);
  const [password, setPassword] = useState("••••••••••••");

  const handleSelectPersona = (persona: PersonaType) => {
    setSelectedPersona(persona);
    setEmail(PRESET_PERSONAS[persona].email);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(selectedPersona);
    router.push("/workspace");
  };

  return (
    <div className="min-h-screen flex items-stretch">
      {/* Left Artwork & Slogan Panel (45%) */}
      <div className="hidden lg:flex lg:w-5/12 bg-slate-950 text-white flex-col justify-between p-10 border-r border-slate-800 relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-primary/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-emerald/10 rounded-full blur-3xl pointer-events-none" />

        {/* Brand Top */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary text-white grid place-items-center shadow-lg font-bold">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <span className="font-extrabold text-base tracking-tight block">
              QueryPilot
            </span>
            <span className="text-[10px] text-slate-400 uppercase tracking-widest block font-mono">
              AI Data Workspace
            </span>
          </div>
        </div>

        {/* Center Pitch & Trust Badges */}
        <div className="relative z-10 space-y-6 my-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald animate-pulse" />
            <span>TPC-DS Retail Benchmark (24 Tables)</span>
          </div>

          <h1 className="text-3xl font-extrabold leading-tight tracking-tight text-slate-100">
            Turn business questions into verified SQL & visualizations.
          </h1>

          <p className="text-xs text-slate-400 leading-relaxed max-w-md">
            QueryPilot provides self-service enterprise analytics across Store, Web, and Catalog channels — protected by deterministic AST sanitization and RBAC cost guards.
          </p>

          <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-800/80">
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xl font-extrabold text-white font-mono block">
                24 Tables
              </span>
              <span className="text-[11px] text-slate-400 block mt-0.5">
                Constellation schema
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xl font-extrabold text-emerald font-mono block">
                100% Verified
              </span>
              <span className="text-[11px] text-slate-400 block mt-0.5">
                sqlglot AST checks
              </span>
            </div>
          </div>
        </div>

        {/* Bottom Quote */}
        <div className="relative z-10 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
          <span>Version 3.0 · DuckDB In-Memory OLAP</span>
          <span className="font-mono text-[10px] text-slate-500">TPC-DS 2003</span>
        </div>
      </div>

      {/* Right Login & Persona Selection Panel (55%) */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12 bg-canvas">
        <div className="w-full max-w-md space-y-6">
          {/* Header */}
          <div className="space-y-1">
            <h2 className="text-2xl font-extrabold tracking-tight text-foreground">
              Welcome to QueryPilot
            </h2>
            <p className="text-xs text-muted leading-relaxed">
              Sign in to access self-service analytics workspace or select a demo role below.
            </p>
          </div>

          {/* Quick Demo Personas */}
          <div className="space-y-2.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted block">
              1-Click Demo Persona
            </span>
            <div className="grid grid-cols-2 gap-2.5">
              {/* Analyst */}
              <button
                type="button"
                onClick={() => handleSelectPersona("analyst")}
                className={`p-3 rounded-xl text-left border transition-all ${
                  selectedPersona === "analyst"
                    ? "bg-surface border-primary ring-2 ring-primary/20 shadow-sm"
                    : "bg-surface-2 border-line hover:bg-surface text-muted"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="p-1.5 rounded-lg bg-primary-soft text-primary">
                    <User className="w-3.5 h-3.5" />
                  </div>
                  {selectedPersona === "analyst" && (
                    <Check className="w-3.5 h-3.5 text-primary" />
                  )}
                </div>
                <strong className="text-xs font-bold text-foreground block">
                  Alex Chen
                </strong>
                <span className="text-[10px] text-muted block">
                  Data Analyst
                </span>
              </button>

              {/* Admin */}
              <button
                type="button"
                onClick={() => handleSelectPersona("admin")}
                className={`p-3 rounded-xl text-left border transition-all ${
                  selectedPersona === "admin"
                    ? "bg-surface border-primary ring-2 ring-primary/20 shadow-sm"
                    : "bg-surface-2 border-line hover:bg-surface text-muted"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="p-1.5 rounded-lg bg-emerald-soft text-emerald">
                    <Shield className="w-3.5 h-3.5" />
                  </div>
                  {selectedPersona === "admin" && (
                    <Check className="w-3.5 h-3.5 text-emerald" />
                  )}
                </div>
                <strong className="text-xs font-bold text-foreground block">
                  Sarah Data Lead
                </strong>
                <span className="text-[10px] text-muted block">
                  Admin (HITL Rights)
                </span>
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-foreground block">
                Work Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-line bg-surface text-foreground focus:outline-none focus:border-primary shadow-xs"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-bold text-foreground">
                  Password
                </label>
                <span className="text-[10px] text-muted">Demo mode (bypassed)</span>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-line bg-surface text-foreground focus:outline-none focus:border-primary shadow-xs font-mono"
              />
            </div>

            <button
              type="submit"
              className="w-full py-2.5 rounded-xl bg-primary hover:bg-primary-strong text-white font-bold text-xs flex items-center justify-center gap-2 transition shadow-sm"
            >
              <span>Sign in to Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* Footnote */}
          <p className="text-[10px] text-center text-muted">
            Authenticated via enterprise RBAC token headers. No third-party cookies required.
          </p>
        </div>
      </div>
    </div>
  );
}
