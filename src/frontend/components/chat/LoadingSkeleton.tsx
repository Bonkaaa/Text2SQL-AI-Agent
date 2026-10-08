"use client";

import React from "react";

export interface LoadingSkeletonProps {
  className?: string;
}

export function LoadingSkeleton({ className = "" }: LoadingSkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Đang phân tích số liệu..."
      className={`space-y-4 w-full animate-in fade-in duration-200 ${className}`}
    >
      {/* 1. KPI Cards Row Skeleton (3 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            data-testid="kpi-skeleton-card"
            className="p-3.5 rounded-xl bg-surface border border-surface-border animate-pulse space-y-2"
          >
            <div className="h-3 w-20 bg-surface-secondary rounded" />
            <div className="h-6 w-28 bg-surface-tertiary rounded" />
            <div className="h-2.5 w-16 bg-surface-secondary/80 rounded" />
          </div>
        ))}
      </div>

      {/* 2. Chart Area Skeleton */}
      <div
        data-testid="chart-skeleton-area"
        className="p-4 rounded-xl bg-surface border border-surface-border animate-pulse space-y-3"
      >
        <div className="flex items-center justify-between">
          <div className="h-3.5 w-32 bg-surface-secondary rounded" />
          <div className="h-3 w-16 bg-surface-secondary rounded" />
        </div>
        <div className="h-44 w-full bg-surface-secondary/50 rounded-lg flex items-end justify-between p-3 gap-2">
          {[40, 65, 80, 50, 90, 70, 85].map((heightPct, idx) => (
            <div
              key={idx}
              className="flex-1 bg-surface-tertiary/70 rounded-t"
              style={{ height: `${heightPct}%` }}
            />
          ))}
        </div>
      </div>

      {/* 3. Table Rows Skeleton */}
      <div className="p-3 rounded-xl bg-surface border border-surface-border animate-pulse space-y-2">
        <div className="flex items-center justify-between pb-1.5 border-b border-surface-border/60">
          <div className="h-3 w-24 bg-surface-secondary rounded" />
          <div className="h-3 w-12 bg-surface-secondary rounded" />
        </div>
        {[1, 2, 3].map((row) => (
          <div
            key={row}
            data-testid="table-row-skeleton"
            className="flex items-center justify-between py-1.5 gap-4"
          >
            <div className="h-3 w-1/4 bg-surface-secondary/80 rounded" />
            <div className="h-3 w-1/3 bg-surface-tertiary/60 rounded" />
            <div className="h-3 w-1/6 bg-surface-secondary/80 rounded" />
            <div className="h-3 w-1/5 bg-surface-tertiary/70 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}
