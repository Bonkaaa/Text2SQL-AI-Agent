"use client";

import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { BarChart3, LineChart as LineIcon, AreaChart as AreaIcon, PieChart as PieIcon } from "lucide-react";
import { QueryResponse, ChartArtifact } from "@/types/api";
import { formatNumber, formatCurrency } from "@/lib/formatters";

interface ChartViewProps {
  response: QueryResponse;
}

const PALETTE = ["#5B5BD6", "#17845D", "#A86812", "#8B5CF6", "#06B6D4", "#EC4899"];

export function ChartView({ response }: ChartViewProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [chartTypeOverride, setChartTypeOverride] = useState<"bar" | "line" | "area" | "pie" | null>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // 1. Try finding typed chart artifact from response_package
  const chartArtifact = response.response_package?.artifacts?.find(
    (a) => a.type === "chart"
  ) as ChartArtifact | undefined;

  // 2. Try legacy recharts_config
  const legacyConfig = response.recharts_config;

  // 3. Fallback derivation from raw data
  let data: Record<string, any>[] = [];
  let xKey = "";
  let yKeys: string[] = [];
  let title = "";
  let baseType: "bar" | "line" | "area" | "pie" = "bar";

  if (chartArtifact) {
    data = chartArtifact.data || [];
    xKey = chartArtifact.x_key;
    yKeys = chartArtifact.y_keys || [];
    title = chartArtifact.title || "Data Visualization";
    baseType = (chartArtifact.chart_type === "composed" ? "bar" : chartArtifact.chart_type) || "bar";
  } else if (legacyConfig) {
    data = legacyConfig.data || response.data || [];
    xKey = legacyConfig.x_axis || "";
    yKeys = (legacyConfig.series || []).map((s: any) => (typeof s === "string" ? s : s.key));
    title = legacyConfig.title || "Data Visualization";
    baseType = legacyConfig.type || "bar";
  } else if (response.data && response.data.length > 0 && response.columns && response.columns.length > 1) {
    data = response.data;
    xKey = response.columns[0];
    yKeys = response.columns.slice(1).filter((col) => {
      return data.some((r) => typeof r[col] === "number");
    });
    title = "Query Result Chart";
    baseType = "bar";
  }

  const activeType = chartTypeOverride || baseType;

  if (!data || data.length === 0 || !xKey || yKeys.length === 0) {
    return (
      <div className="bg-surface border border-line rounded-xl p-8 text-center text-muted text-xs">
        No numeric series found to construct visualization. Switch to Table view to inspect raw data.
      </div>
    );
  }

  if (!isMounted) {
    return (
      <div className="h-[360px] bg-surface border border-line rounded-xl flex items-center justify-center text-xs text-muted">
        Loading chart container...
      </div>
    );
  }

  const renderChart = () => {
    switch (activeType) {
      case "line":
        return (
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e9f1" />
              <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "#64748b" }} dy={8} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => formatNumber(v)} />
              <Tooltip
                formatter={(val: any) => [typeof val === "number" ? formatNumber(val) : val, ""]}
                contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e9f1", borderRadius: "8px", fontSize: "12px" }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
              {yKeys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={PALETTE[idx % PALETTE.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case "area":
        return (
          <ResponsiveContainer width="100%" height={340}>
            <AreaChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e9f1" />
              <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "#64748b" }} dy={8} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => formatNumber(v)} />
              <Tooltip
                formatter={(val: any) => [typeof val === "number" ? formatNumber(val) : val, ""]}
                contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e9f1", borderRadius: "8px", fontSize: "12px" }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
              {yKeys.map((key, idx) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={PALETTE[idx % PALETTE.length]}
                  fill={PALETTE[idx % PALETTE.length]}
                  fillOpacity={0.2}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        );

      case "pie":
        const pieValueKey = yKeys[0];
        return (
          <ResponsiveContainer width="100%" height={340}>
            <PieChart>
              <Tooltip
                formatter={(val: any) => [typeof val === "number" ? formatNumber(val) : val, ""]}
                contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e9f1", borderRadius: "8px", fontSize: "12px" }}
              />
              <Legend wrapperStyle={{ fontSize: "11px" }} />
              <Pie
                data={data}
                dataKey={pieValueKey}
                nameKey={xKey}
                cx="50%"
                cy="50%"
                outerRadius={110}
                label={(entry) => `${entry[xKey]}: ${formatNumber(entry[pieValueKey])}`}
              >
                {data.map((_, idx) => (
                  <Cell key={`cell-${idx}`} fill={PALETTE[idx % PALETTE.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        );

      case "bar":
      default:
        return (
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e9f1" />
              <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "#64748b" }} dy={8} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => formatNumber(v)} />
              <Tooltip
                formatter={(val: any) => [typeof val === "number" ? formatNumber(val) : val, ""]}
                contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e9f1", borderRadius: "8px", fontSize: "12px" }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
              {yKeys.map((key, idx) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={PALETTE[idx % PALETTE.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <div className="space-y-3">
      {/* Chart Header & Type Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-surface border border-line rounded-xl shadow-card">
        <div>
          <h4 className="text-xs font-bold text-foreground">{title}</h4>
          <span className="text-[10px] text-muted">
            X: <span className="font-mono text-foreground">{xKey}</span> • Y:{" "}
            <span className="font-mono text-foreground">{yKeys.join(", ")}</span>
          </span>
        </div>

        <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg border border-line">
          <button
            type="button"
            onClick={() => setChartTypeOverride("bar")}
            className={`p-1.5 rounded transition-colors ${
              activeType === "bar"
                ? "bg-surface shadow-xs text-primary font-bold"
                : "text-muted hover:text-foreground"
            }`}
            title="Bar Chart"
          >
            <BarChart3 className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setChartTypeOverride("line")}
            className={`p-1.5 rounded transition-colors ${
              activeType === "line"
                ? "bg-surface shadow-xs text-primary font-bold"
                : "text-muted hover:text-foreground"
            }`}
            title="Line Chart"
          >
            <LineIcon className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setChartTypeOverride("area")}
            className={`p-1.5 rounded transition-colors ${
              activeType === "area"
                ? "bg-surface shadow-xs text-primary font-bold"
                : "text-muted hover:text-foreground"
            }`}
            title="Area Chart"
          >
            <AreaIcon className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setChartTypeOverride("pie")}
            className={`p-1.5 rounded transition-colors ${
              activeType === "pie"
                ? "bg-surface shadow-xs text-primary font-bold"
                : "text-muted hover:text-foreground"
            }`}
            title="Pie Chart"
          >
            <PieIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="bg-surface border border-line rounded-xl p-4 shadow-card">
        {renderChart()}
      </div>
    </div>
  );
}
