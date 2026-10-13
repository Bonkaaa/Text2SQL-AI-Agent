"use client";

import React, { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { TableMetadata, TableCategory } from "@/types/schema";
import { TableDetailView } from "./TableDetailView";
import { formatNumber } from "@/lib/formatters";
import { useLanguage } from "@/context/LanguageContext";

interface SchemaExplorerProps {
  tables: TableMetadata[];
  selectedTable?: TableMetadata | null;
  onSelectTable: (table: TableMetadata) => void;
  onAskQuestion: (question: string) => void;
}

type FilterCategory = "all" | TableCategory;

export function SchemaExplorer({
  tables,
  selectedTable,
  onSelectTable,
  onAskQuestion,
}: SchemaExplorerProps) {
  const { t } = useLanguage();
  const [activeCategory, setActiveCategory] = useState<FilterCategory>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const categories: { id: FilterCategory; label: string; count: number }[] = [
    { id: "all", label: t("sources.allTables", "All Tables"), count: tables.length },
    {
      id: "transactions",
      label: t("sources.catTransactions", "Transactions"),
      count: tables.filter((t) => t.category === "transactions").length,
    },
    {
      id: "products_inventory",
      label: t("sources.catProductsInventory", "Products & Inventory"),
      count: tables.filter((t) => t.category === "products_inventory").length,
    },
    {
      id: "partners_customers",
      label: t("sources.catPartnersCustomers", "Partners & Customers"),
      count: tables.filter((t) => t.category === "partners_customers").length,
    },
    {
      id: "geography",
      label: t("sources.catGeography", "Geography"),
      count: tables.filter((t) => t.category === "geography").length,
    },
  ];

  const filteredTables = useMemo(() => {
    return tables.filter((t) => {
      const matchCat =
        activeCategory === "all" || t.category === activeCategory;
      if (!matchCat) return false;

      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        t.name.toLowerCase().includes(q) ||
        t.displayName.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.columns.some((c) => c.name.toLowerCase().includes(q))
      );
    });
  }, [tables, activeCategory, searchQuery]);

  const currentSelected =
    selectedTable || filteredTables[0] || tables[0] || null;

  return (
    <div className="space-y-4">
      {/* Category Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Category Tab Bar */}
        <div
          role="tablist"
          aria-label="Table Categories"
          className="flex items-center gap-1 overflow-x-auto bg-surface-2 p-1 rounded-xl border border-line"
        >
          {categories.map((cat) => {
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                role="tab"
                id={`tab-${cat.id}`}
                aria-selected={isActive}
                type="button"
                onClick={() => setActiveCategory(cat.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? "bg-surface text-primary shadow-xs font-bold"
                    : "text-muted hover:text-foreground hover:bg-surface/50"
                }`}
              >
                <span>{cat.label}</span>
                <span
                  className={`text-[10px] font-mono tabular-nums px-1.5 py-0.2 rounded-full ${
                    isActive
                      ? "bg-primary-soft text-primary font-bold"
                      : "bg-surface text-muted"
                  }`}
                >
                  {cat.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search input */}
        <div className="relative sm:w-64">
          <Search className="w-3.5 h-3.5 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={t("sources.searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-line bg-surface text-foreground placeholder:text-muted focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      {/* Main 2-Column Split: Table List (left) + Table Detail (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left: Table List (4 cols) */}
        <div className="lg:col-span-4 bg-surface border border-line rounded-xl shadow-card overflow-hidden">
          <div className="p-3 border-b border-line bg-surface-2 flex items-center justify-between text-xs font-bold text-foreground">
            <span>
              {t("sources.tablesHeader", "TPC-H Tables")} ({filteredTables.length})
            </span>
            <span className="text-[10px] text-muted font-normal">
              {t("sources.clickToInspect")}
            </span>
          </div>

          <div className="divide-y divide-line max-h-[620px] overflow-y-auto">
            {filteredTables.length === 0 ? (
              <div className="p-6 text-center text-xs text-muted">
                {t("sources.noTablesMatch")}
              </div>
            ) : (
              filteredTables.map((tItem) => {
                const isSelected = currentSelected?.name === tItem.name;
                return (
                  <button
                    key={tItem.name}
                    type="button"
                    onClick={() => onSelectTable(tItem)}
                    className={`w-full text-left p-3 transition-colors flex items-start justify-between gap-2 ${
                      isSelected
                        ? "bg-primary-soft/40 border-l-4 border-l-primary"
                        : "hover:bg-surface-2"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-bold text-foreground truncate">
                          {tItem.name}
                        </span>
                      </div>
                      <span className="text-[11px] text-muted block truncate mt-0.5">
                        {tItem.displayName}
                      </span>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="text-[10px] font-mono tabular-nums text-muted block">
                        ~{formatNumber(tItem.rowCountEstimate)}
                      </span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-2 text-muted border border-line mt-1 inline-block">
                        {tItem.columns.length} {t("sources.cols")}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Table Detail Inspector (8 cols) */}
        <div className="lg:col-span-8">
          {currentSelected ? (
            <TableDetailView
              table={currentSelected}
              onAskQuestion={onAskQuestion}
            />
          ) : (
            <div className="bg-surface border border-line rounded-xl p-12 text-center text-xs text-muted">
              {t("sources.selectToInspect")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
