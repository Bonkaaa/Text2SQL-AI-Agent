"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { DataSourceCard } from "@/components/sources/DataSourceCard";
import { SchemaExplorer } from "@/components/sources/SchemaExplorer";
import { TPCDS_TABLES } from "@/data/tpcdsCatalog";
import { TableMetadata } from "@/types/schema";

export default function DataSourcesPage() {
  const router = useRouter();
  const [selectedTable, setSelectedTable] = useState<TableMetadata | null>(
    TPCDS_TABLES[0]
  );
  const [isSyncing, setIsSyncing] = useState(false);

  const handleAskQuestion = (question: string) => {
    router.push(`/workspace?q=${encodeURIComponent(question)}`);
  };

  const handleSyncSchema = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
    }, 600);
  };

  return (
    <div className="space-y-6">
      {/* Page Heading & Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <div className="text-primary text-[10px] font-extrabold uppercase tracking-widest mb-1.5">
            Enterprise Warehouse Schema
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            Data sources & Schema
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1 max-w-2xl leading-relaxed">
            Manage data warehouse connections and inspect the ground-truth schema of 24 TPC-DS tables.
          </p>
        </div>

        <button
          type="button"
          onClick={handleSyncSchema}
          disabled={isSyncing}
          className="inline-flex items-center gap-2 bg-primary hover:bg-primary-strong text-white px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
          <span>{isSyncing ? "Syncing..." : "Sync schema"}</span>
        </button>
      </div>

      {/* Connection Card Top */}
      <DataSourceCard tableCount={TPCDS_TABLES.length} />

      {/* Schema Explorer & Table Inspector */}
      <SchemaExplorer
        tables={TPCDS_TABLES}
        selectedTable={selectedTable}
        onSelectTable={setSelectedTable}
        onAskQuestion={handleAskQuestion}
      />

      {/* Footer Navigation Link */}
      <div className="flex items-center justify-between text-xs text-muted pt-2 border-t border-line">
        <span>TPC-DS Retail Schema (24 Tables) · Omnichannel Constellation</span>
        <Link
          href="/workspace"
          className="text-primary font-bold hover:underline inline-flex items-center gap-1"
        >
          Open Analytics Workspace <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
