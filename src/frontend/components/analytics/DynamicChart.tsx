"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
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
} from "recharts";
import {
  BarChart3,
  LineChart as LineIcon,
  AreaChart as AreaIcon,
  PieChart as PieIcon,
  HelpCircle,
} from "lucide-react";
import { ChartType, RechartsConfig } from "@/types/api";

const PALETTE = [
  "#6366f1", // Indigo
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#06b6d4", // Cyan
  "#ec4899", // Rose
  "#8b5cf6", // Purple
  "#14b8a6", // Teal
  "#f97316", // Orange
];

export interface DynamicChartProps {
  config: RechartsConfig;
  data: Record<string, any>[];
  className?: string;
  height?: number;
}

/**
 * Định dạng số hiển thị trên nhãn trục và tooltip
 */
function formatNumber(value: any): string {
  if (typeof value === "number") {
    if (Math.abs(value) >= 1_000_000_000) {
      return `${(value / 1_000_000_000).toFixed(1)}B`;
    }
    if (Math.abs(value) >= 1_000_000) {
      return `${(value / 1_000_000).toFixed(1)}M`;
    }
    if (Math.abs(value) >= 1_000) {
      return `${(value / 1_000).toFixed(1)}K`;
    }
    return value.toLocaleString("vi-VN");
  }
  return String(value ?? "");
}

/**
 * Custom Dark Mode Tooltip cho Recharts
 */
function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-slate-700/80 bg-[#0c1322]/95 p-3 shadow-2xl backdrop-blur-md text-xs space-y-1.5 z-50">
        <p className="font-semibold text-slate-200 border-b border-slate-700/50 pb-1">
          {label}
        </p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-slate-400">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: entry.color || entry.fill }}
              />
              <span>{entry.name}:</span>
            </span>
            <span className="font-mono font-semibold text-slate-100">
              {typeof entry.value === "number"
                ? entry.value.toLocaleString("vi-VN")
                : entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
}

export function DynamicChart({
  config,
  data,
  className = "",
  height = 320,
}: DynamicChartProps) {
  // Trạng thái cho phép đổi loại biểu đồ tương tác
  const [currentType, setCurrentType] = useState<ChartType>(
    config?.chart_type === "table" ? "bar" : config?.chart_type || "bar"
  );

  // Kiểm tra dữ liệu rỗng
  if (!data || data.length === 0) {
    return (
      <div
        className={`rounded-2xl border border-surface-border bg-surface/30 p-8 text-center space-y-2 backdrop-blur-sm ${className}`}
        role="region"
        aria-label="Biểu đồ không có dữ liệu"
      >
        <HelpCircle className="w-8 h-8 text-slate-500 mx-auto" />
        <p className="text-xs text-slate-400">
          Không có dữ liệu để vẽ biểu đồ
        </p>
      </div>
    );
  }

  // Xác định trục X và các chuỗi dữ liệu trục Y
  const xAxisKey =
    config.x_key ||
    config.x_axis ||
    (data[0] ? Object.keys(data[0])[0] : "name");

  let yKeys: string[] = [];
  if (config.y_keys && config.y_keys.length > 0) {
    yKeys = config.y_keys;
  } else if (config.y_axis) {
    yKeys = Array.isArray(config.y_axis) ? config.y_axis : [config.y_axis];
  } else if (data[0]) {
    yKeys = Object.keys(data[0]).filter((k) => k !== xAxisKey);
  }

  // Lấy nhãn hiển thị thân thiện
  const getSeriesLabel = (key: string) => {
    return config.series_labels?.[key] || key;
  };

  const chartTypes: { type: ChartType; label: string; icon: any }[] = [
    { type: "bar", label: "Cột", icon: BarChart3 },
    { type: "line", label: "Đường", icon: LineIcon },
    { type: "area", label: "Miền", icon: AreaIcon },
    { type: "pie", label: "Tròn", icon: PieIcon },
  ];

  return (
    <div
      className={`rounded-2xl border border-surface-border bg-gradient-to-br from-[#0c1322]/90 via-[#0a0f1d]/90 to-[#070b14]/90 p-4 sm:p-5 space-y-4 backdrop-blur-md shadow-card transition-all ${className}`}
      role="region"
      aria-label="Biểu đồ trực quan hóa dữ liệu TPC-H"
    >
      {/* Header & Chart Type Switcher Toolbar */}
      <div className="flex items-start justify-between gap-3 flex-wrap border-b border-surface-border pb-3">
        <div>
          {config.title && (
            <h4 className="text-xs font-bold text-slate-200 tracking-wide uppercase">
              {config.title}
            </h4>
          )}
          {config.description && (
            <p className="text-[11px] text-slate-400 mt-0.5">
              {config.description}
            </p>
          )}
        </div>

        {/* Switcher Buttons */}
        <div
          className="flex items-center gap-1 bg-surface-subtle/80 p-1 rounded-xl border border-surface-border"
          role="toolbar"
          aria-label="Chuyển đổi loại biểu đồ"
        >
          {chartTypes.map(({ type, label, icon: Icon }) => {
            const isActive = currentType === type;
            return (
              <button
                key={type}
                type="button"
                onClick={() => setCurrentType(type)}
                aria-pressed={isActive}
                aria-label={`Biểu đồ ${label}`}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? "bg-brand-500/20 text-brand-300 border border-brand-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface/50 border border-transparent"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="w-full pt-1" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%" minWidth={200} minHeight={200}>
          {currentType === "bar" ? (
            <BarChart
              data={data}
              margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#1e293b"
                vertical={false}
              />
              <XAxis
                dataKey={xAxisKey}
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={false}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={false}
                tickFormatter={formatNumber}
              />
              <Tooltip content={<CustomTooltip />} />
              {config.legend !== false && (
                <Legend
                  wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                  formatter={(value) => (
                    <span className="text-slate-300">{getSeriesLabel(value)}</span>
                  )}
                />
              )}
              {yKeys.map((key, idx) => (
                <Bar
                  key={key}
                  dataKey={key}
                  name={getSeriesLabel(key)}
                  fill={PALETTE[idx % PALETTE.length]}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={48}
                />
              ))}
            </BarChart>
          ) : currentType === "line" ? (
            <LineChart
              data={data}
              margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#1e293b"
                vertical={false}
              />
              <XAxis
                dataKey={xAxisKey}
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={false}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={false}
                tickFormatter={formatNumber}
              />
              <Tooltip content={<CustomTooltip />} />
              {config.legend !== false && (
                <Legend
                  wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                  formatter={(value) => (
                    <span className="text-slate-300">{getSeriesLabel(value)}</span>
                  )}
                />
              )}
              {yKeys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={getSeriesLabel(key)}
                  stroke={PALETTE[idx % PALETTE.length]}
                  strokeWidth={2.5}
                  dot={{ fill: PALETTE[idx % PALETTE.length], r: 3.5 }}
                  activeDot={{ r: 6 }}
                />
              ))}
            </LineChart>
          ) : currentType === "area" ? (
            <AreaChart
              data={data}
              margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
            >
              <defs>
                {yKeys.map((key, idx) => (
                  <linearGradient
                    key={`gradient-${key}`}
                    id={`areaGradient-${key}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="5%"
                      stopColor={PALETTE[idx % PALETTE.length]}
                      stopOpacity={0.4}
                    />
                    <stop
                      offset="95%"
                      stopColor={PALETTE[idx % PALETTE.length]}
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#1e293b"
                vertical={false}
              />
              <XAxis
                dataKey={xAxisKey}
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={false}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={false}
                tickFormatter={formatNumber}
              />
              <Tooltip content={<CustomTooltip />} />
              {config.legend !== false && (
                <Legend
                  wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                  formatter={(value) => (
                    <span className="text-slate-300">{getSeriesLabel(value)}</span>
                  )}
                />
              )}
              {yKeys.map((key, idx) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={getSeriesLabel(key)}
                  stroke={PALETTE[idx % PALETTE.length]}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill={`url(#areaGradient-${key})`}
                />
              ))}
            </AreaChart>
          ) : (
            <PieChart>
              <Tooltip content={<CustomTooltip />} />
              {config.legend !== false && (
                <Legend
                  wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                  formatter={(value) => (
                    <span className="text-slate-300">{value}</span>
                  )}
                />
              )}
              <Pie
                data={data}
                dataKey={yKeys[0] || Object.keys(data[0] || {})[1]}
                nameKey={xAxisKey}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={85}
                paddingAngle={3}
              >
                {data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={PALETTE[index % PALETTE.length]}
                  />
                ))}
              </Pie>
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default DynamicChart;
