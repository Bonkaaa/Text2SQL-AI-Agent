"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { DataSourceCard } from "@/components/sources/DataSourceCard";
import { SchemaExplorer } from "@/components/sources/SchemaExplorer";
import { TPCH_TABLES } from "@/data/tpchCatalog";
import { TableMetadata } from "@/types/schema";
import { useLanguage } from "@/context/LanguageContext";

export default function DataSourcesPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const [selectedTable, setSelectedTable] = useState<TableMetadata | null>(
    TPCH_TABLES[0]
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
            {t("sources.eyebrow")}
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            {t("sources.title")}
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1 max-w-2xl leading-relaxed">
            {t("sources.description")}
          </p>
        </div>

        <button
          type="button"
          onClick={handleSyncSchema}
          disabled={isSyncing}
          className="inline-flex items-center gap-2 bg-primary hover:bg-primary-strong text-white px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
          <span>{isSyncing ? t("sources.syncing") : t("sources.syncSchema")}</span>
        </button>
      </div>

      {/* Connection Card Top */}
      <DataSourceCard tableCount={TPCH_TABLES.length} />

      {/* Schema Explorer & Table Inspector */}
      <SchemaExplorer
        tables={TPCH_TABLES}
        selectedTable={selectedTable}
        onSelectTable={setSelectedTable}
        onAskQuestion={handleAskQuestion}
      />
    </div>
  );
}
