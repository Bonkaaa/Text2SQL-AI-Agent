"use client";

import React, { useMemo } from "react";
import {
  LayoutGrid,
  TrendingUp,
  CheckCircle2,
  Clock,
  Bookmark,
  Play,
  Database,
  History as HistoryIcon,
  Settings,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryHistory } from "@/hooks/useQueryHistory";
import { useSavedQueries } from "@/hooks/useSavedQueries";
import { ActivityChart } from "@/components/dashboard/ActivityChart";

const POPULAR_RECOMMENDED_QUERIES = [
  {
    title: "Top 10 Sản Phẩm Doanh Thu Cao Nhất 2003",
    question: "Which 10 products generated the most revenue in 2003?",
    category: "Store Sales",
    runs: 42,
  },
  {
    title: "So Sánh Doanh Số Kênh Cửa Hàng vs Kênh Web 2002",
    question: "Compare monthly sales between store channel and web channel in 2002.",
    category: "Omnichannel",
    runs: 31,
  },
  {
    title: "Phân Tích Tỷ Lệ Đổi Trả Theo Nhóm Học Vấn",
    question: "Which customer income demographics show the highest item return rate?",
    category: "Customer & Returns",
    runs: 28,
  },
  {
    title: "Tồn Kho Mặt Hàng Apparel Tại Kho Số 1",
    question: "Tồn kho các mặt hàng thuộc nhóm Apparel tại kho số 1",
    category: "Inventory",
    runs: 19,
  },
];

export default function DashboardPage() {
  const router = useRouter();
  const { historyItems } = useQueryHistory();
  const { savedQueries } = useSavedQueries();

  const metrics = useMemo(() => {
    const total = historyItems.length;
    const successItems = historyItems.filter((item) => item.status === "SUCCESS");
    const successCount = successItems.length;
    const rate = total > 0 ? ((successCount / total) * 100).toFixed(1) : "0.0";

    const latencyItems = successItems.filter(
      (item) => typeof item.executionTimeMs === "number"
    );
    const avgLatency =
      latencyItems.length > 0
        ? Math.round(
            latencyItems.reduce((acc, item) => acc + (item.executionTimeMs || 0), 0) /
              latencyItems.length
          )
        : 0;

    return {
      totalQueries: total,
      successRate: `${rate}%`,
      avgLatencyMs: `${avgLatency}ms`,
      savedCount: savedQueries.length,
    };
  }, [historyItems, savedQueries]);

  const handleRunQuery = (question: string) => {
    router.push(`/workspace?q=${encodeURIComponent(question)}`);
  };

  return (
    <div className="space-y-6">
      {/* Page Heading */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <div className="text-primary text-[10px] font-extrabold uppercase tracking-widest mb-1.5">
            Analytics at a glance
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            Workspace Dashboard
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1 max-w-2xl leading-relaxed">
            A home for reusable insights, saved visualizations, and warehouse query telemetry.
          </p>
        </div>

        <Link
          href="/workspace"
          className="inline-flex items-center gap-2 bg-primary hover:bg-primary-strong text-white px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-sm"
        >
          <LayoutGrid className="w-4 h-4" />
          Launch workspace
        </Link>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface border border-line rounded-xl p-4 shadow-panel">
          <div className="flex items-center justify-between text-muted text-xs font-semibold">
            <span>Total Queries Run</span>
            <div className="w-7 h-7 rounded-lg bg-primary-soft text-primary grid place-items-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div
            data-testid="kpi-total-queries"
            className="text-2xl font-extrabold text-foreground mt-3 tracking-tight font-mono tabular-nums"
          >
            {metrics.totalQueries}
          </div>
          <div className="text-[10px] text-muted mt-1.5">
            <span className="text-emerald font-bold">Live telemetry</span> from session history
          </div>
        </div>

        <div className="bg-surface border border-line rounded-xl p-4 shadow-panel">
          <div className="flex items-center justify-between text-muted text-xs font-semibold">
            <span>Execution Success Rate</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-soft text-emerald grid place-items-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div
            data-testid="kpi-success-rate"
            className="text-2xl font-extrabold text-foreground mt-3 tracking-tight font-mono tabular-nums"
          >
            {metrics.successRate}
          </div>
          <div className="text-[10px] text-muted mt-1.5">
            AST validated & read-only enforced
          </div>
        </div>

        <div className="bg-surface border border-line rounded-xl p-4 shadow-panel">
          <div className="flex items-center justify-between text-muted text-xs font-semibold">
            <span>Avg. Execution Latency</span>
            <div className="w-7 h-7 rounded-lg bg-primary-soft text-primary grid place-items-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div
            data-testid="kpi-avg-latency"
            className="text-2xl font-extrabold text-foreground mt-3 tracking-tight font-mono tabular-nums"
          >
            {metrics.avgLatencyMs}
          </div>
          <div className="text-[10px] text-muted mt-1.5">
            DuckDB in-process OLAP speed
          </div>
        </div>

        <div className="bg-surface border border-line rounded-xl p-4 shadow-panel">
          <div className="flex items-center justify-between text-muted text-xs font-semibold">
            <span>Saved Insights</span>
            <div className="w-7 h-7 rounded-lg bg-amber-soft text-amber grid place-items-center">
              <Bookmark className="w-4 h-4" />
            </div>
          </div>
          <div
            data-testid="kpi-saved-queries"
            className="text-2xl font-extrabold text-foreground mt-3 tracking-tight font-mono tabular-nums"
          >
            {metrics.savedCount} {metrics.savedCount === 1 ? "Query" : "Queries"}
          </div>
          <div className="text-[10px] text-muted mt-1.5">
            Pinned in saved queries library
          </div>
        </div>
      </div>

      {/* Two Column Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* 7-Day Chart */}
        <div className="lg:col-span-7 xl:col-span-8 bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <strong className="text-xs font-bold text-foreground block">
                7-Day Query Activity Volume
              </strong>
              <small className="text-[10px] text-muted">
                Daily executed analytical requests
              </small>
            </div>
            <span className="text-[10px] border border-line rounded px-2 py-1 bg-surface-2 text-muted">
              Last 7 Days
            </span>
          </div>

          <ActivityChart historyItems={historyItems} />
        </div>

        {/* Popular / Recommended Queries */}
        <div className="lg:col-span-5 xl:col-span-4 bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-3 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-line pb-2.5">
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-primary" />
                <strong className="text-xs font-bold text-foreground">Popular Queries</strong>
              </div>
              <Link href="/saved-queries" className="text-[10px] text-primary font-bold hover:underline">
                View all library
              </Link>
            </div>

            <div className="space-y-2.5">
              {POPULAR_RECOMMENDED_QUERIES.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-surface-2 border border-line hover:border-primary/40 transition flex flex-col gap-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-foreground text-xs leading-snug">
                      {item.title}
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface border border-line text-muted font-mono shrink-0">
                      {item.runs} runs
                    </span>
                  </div>
                  <p className="text-[11px] text-muted line-clamp-1 italic">
                    &quot;{item.question}&quot;
                  </p>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] text-primary font-semibold">
                      {item.category}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleRunQuery(item.question)}
                      className="inline-flex items-center gap-1 bg-primary/10 hover:bg-primary text-primary hover:text-white px-2 py-1 rounded text-[11px] font-bold transition"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      Run in Workspace
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Access Shortcuts */}
          <div className="pt-2 border-t border-line grid grid-cols-3 gap-2 text-center">
            <Link
              href="/data-sources"
              className="p-2 rounded-lg bg-surface-2 hover:bg-surface border border-line text-muted hover:text-primary transition flex flex-col items-center gap-1"
            >
              <Database className="w-3.5 h-3.5" />
              <span className="text-[10px] font-bold">24 Tables</span>
            </Link>
            <Link
              href="/history"
              className="p-2 rounded-lg bg-surface-2 hover:bg-surface border border-line text-muted hover:text-primary transition flex flex-col items-center gap-1"
            >
              <HistoryIcon className="w-3.5 h-3.5" />
              <span className="text-[10px] font-bold">Audit Log</span>
            </Link>
            <Link
              href="/settings"
              className="p-2 rounded-lg bg-surface-2 hover:bg-surface border border-line text-muted hover:text-primary transition flex flex-col items-center gap-1"
            >
              <Settings className="w-3.5 h-3.5" />
              <span className="text-[10px] font-bold">Settings</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
