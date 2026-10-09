"use client";

import React, { Suspense, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { Plus, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useWorkspace } from "@/hooks/useWorkspace";
import { ConversationPanel } from "@/components/workspace/ConversationPanel";
import { ResultCanvas } from "@/components/workspace/ResultCanvas";

function WorkspaceInner() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams?.get("q") || null;
  const triggeredRef = useRef(false);

  const {
    messages,
    activeTab,
    setActiveTab,
    isLoading,
    isApproving,
    currentResponse,
    submitQuery,
    approveHitl,
    selectClarificationOption,
    resetConversation,
  } = useWorkspace();

  useEffect(() => {
    if (initialQuery && !triggeredRef.current) {
      triggeredRef.current = true;
      submitQuery(initialQuery);
    }
  }, [initialQuery, submitQuery]);

  return (
    <div className="space-y-5">
      {/* Page Heading & Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <div className="text-primary text-[10px] font-extrabold uppercase tracking-widest mb-1">
            Natural Language Analytics Engine
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            Ask your data.
          </h1>
          <p className="text-muted text-xs md:text-sm mt-0.5 max-w-2xl leading-relaxed">
            Turn business questions into SQL, insights, and visualizations — in one unified workspace.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={resetConversation}
            className="inline-flex items-center gap-2 bg-surface hover:bg-surface-2 text-foreground border border-line-strong px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-sm"
          >
            <Plus className="w-4 h-4 text-primary" />
            New conversation
          </button>
        </div>
      </div>

      {/* 2-Column Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch min-h-[620px]">
        {/* Left Column: Conversation Thread & Composer (5 cols) */}
        <div className="lg:col-span-5 h-[620px]">
          <ConversationPanel
            messages={messages}
            isLoading={isLoading}
            isApproving={isApproving}
            onSubmitQuery={submitQuery}
            onApproveHitl={approveHitl}
            onSelectOption={selectClarificationOption}
            onResetConversation={resetConversation}
          />
        </div>

        {/* Right Column: Result Canvas (7 cols) */}
        <div className="lg:col-span-7 h-[620px] flex flex-col">
          <ResultCanvas
            response={currentResponse}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Footer Navigation Link */}
      <div className="flex items-center justify-between text-xs text-muted pt-2 border-t border-line">
        <span>DuckDB TPC-DS (24 tables) Connected · Least-Privilege Read-Only</span>
        <Link
          href="/data-sources"
          className="text-primary font-bold hover:underline inline-flex items-center gap-1"
        >
          Explore 24 tables in schema explorer <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <Suspense fallback={<div className="p-8 text-xs text-muted">Loading workspace...</div>}>
      <WorkspaceInner />
    </Suspense>
  );
}
