"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { HistoryItem } from "@/lib/storage";

interface ActivityChartProps {
  historyItems?: HistoryItem[];
}

export function ActivityChart({ historyItems = [] }: ActivityChartProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Compute 7-day volume: 6 days ago up to today
  const chartData = useMemo(() => {
    const days: { label: string; dateStr: string; count: number; success: number }[] = [];
    const now = new Date();

    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dayName = d.toLocaleDateString("en-US", { weekday: "short" });
      const datePart = d.toISOString().split("T")[0]; // YYYY-MM-DD
      days.push({
        label: i === 0 ? "Today" : dayName,
        dateStr: datePart,
        count: 0,
        success: 0,
      });
    }

    // Match history items
    if (historyItems.length > 0) {
      historyItems.forEach((item) => {
        const itemDate = item.timestamp?.split(" ")[0] || "";
        const matched = days.find((d) => d.dateStr === itemDate);
        if (matched) {
          matched.count += 1;
          if (item.status === "SUCCESS") matched.success += 1;
        } else {
          // If timestamp is not standard or belongs to today/recent
          days[days.length - 1].count += 1;
          if (item.status === "SUCCESS") days[days.length - 1].success += 1;
        }
      });
    }

    return days;
  }, [historyItems]);

  if (!isMounted) {
    return (
      <div
        data-testid="activity-chart-container"
        className="h-56 bg-surface-2/40 border border-line rounded-lg flex items-center justify-center text-xs text-muted"
      >
        Loading telemetry chart...
      </div>
    );
  }

  return (
    <div data-testid="activity-chart-container" className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%" minHeight={220}>
        <BarChart
          data={chartData}
          margin={{ top: 12, right: 12, left: -20, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e4e9f1" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={{ stroke: "#e4e9f1" }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(91, 91, 214, 0.06)" }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-surface border border-line p-2.5 rounded-lg shadow-card text-xs">
                    <p className="font-bold text-foreground mb-1">{data.label}</p>
                    <p className="text-primary font-mono tabular-nums">
                      Queries: <span className="font-bold">{data.count}</span>
                    </p>
                    <p className="text-emerald font-mono tabular-nums text-[11px]">
                      Successful: {data.success}
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar
            dataKey="count"
            fill="#5B5BD6"
            radius={[4, 4, 0, 0]}
            maxBarSize={32}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
