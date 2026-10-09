"use client";

import React from "react";
import { CheckCircle2, Clock, Database, Layers, Timer } from "lucide-react";
import { QueryResponse } from "@/types/api";
import { formatDuration } from "@/lib/formatters";

interface TraceViewProps {
  response: QueryResponse;
}

export function TraceView({ response }: TraceViewProps) {
  const tasks = response.tasks || [];
  const artifacts = response.artifacts || [];
  const totalDuration = response.execution_time_ms
    ? formatDuration(response.execution_time_ms)
    : "—";

  return (
    <div className="space-y-4">
      {/* Trace Overview Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-surface-2 border border-line rounded-xl">
        <div className="flex items-center gap-2 text-xs text-foreground font-semibold">
          <Layers className="w-4 h-4 text-primary" />
          <span>Execution Provenance & Agent Trace</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted">
          <span className="inline-flex items-center gap-1">
            <Timer className="w-3.5 h-3.5 text-primary" />
            <span className="font-mono tabular-nums font-bold text-foreground">
              {totalDuration}
            </span>
          </span>
          <span>•</span>
          <span>{tasks.length} sub-tasks</span>
          {response.session_id && (
            <>
              <span>•</span>
              <span className="font-mono text-[11px]">{response.session_id}</span>
            </>
          )}
        </div>
      </div>

      {/* Steps List */}
      <div className="space-y-3">
        {tasks.map((task, idx) => {
          // Find associated artifact if available
          const linkedArtifact =
            artifacts.find((a) => a.task_id === task.task_id) ||
            artifacts[idx];

          const tablesUsedStr = linkedArtifact?.tables_used?.join(", ");

          return (
            <div
              key={task.task_id || idx}
              className="bg-surface border border-line rounded-xl p-3.5 shadow-card space-y-2.5 transition-all hover:border-line-2"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 p-1 rounded-full bg-emerald-soft text-emerald">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-muted uppercase">
                        Step {idx + 1}
                      </span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-surface-2 text-muted border border-line">
                        {task.status}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-foreground mt-0.5 leading-snug">
                      {task.description}
                    </p>
                  </div>
                </div>

                {linkedArtifact?.execution_time_ms !== undefined && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-mono tabular-nums font-semibold text-muted bg-surface-2 px-2 py-0.5 rounded border border-line whitespace-nowrap">
                    <Clock className="w-3 h-3 text-muted" />
                    {linkedArtifact.execution_time_ms}ms
                  </span>
                )}
              </div>

              {/* Artifact Metadata Pill Details */}
              {linkedArtifact && (
                <div className="pt-1 border-t border-line/60 flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  {tablesUsedStr && (
                    <div className="inline-flex items-center gap-1">
                      <Database className="w-3 h-3 text-primary" />
                      <span className="text-foreground font-mono">{tablesUsedStr}</span>
                    </div>
                  )}

                  {linkedArtifact.row_count !== undefined && (
                    <>
                      <span>•</span>
                      <span>
                        <strong className="text-foreground font-mono tabular-nums">
                          {linkedArtifact.row_count}
                        </strong>{" "}
                        rows returned
                      </span>
                    </>
                  )}

                  {linkedArtifact.dialect && (
                    <>
                      <span>•</span>
                      <span className="uppercase text-[10px] font-bold">
                        {linkedArtifact.dialect}
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {tasks.length === 0 && artifacts.length > 0 && (
          <div className="space-y-3">
            {artifacts.map((artifact, idx) => (
              <div
                key={artifact.artifact_id || idx}
                className="bg-surface border border-line rounded-xl p-3.5 shadow-card space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground">
                    Query Execution
                  </span>
                  {artifact.execution_time_ms !== undefined && (
                    <span className="text-xs font-mono tabular-nums text-muted">
                      {artifact.execution_time_ms}ms
                    </span>
                  )}
                </div>
                {artifact.tables_used && (
                  <div className="text-xs text-muted">
                    Tables:{" "}
                    <span className="text-foreground font-mono">
                      {artifact.tables_used.join(", ")}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {tasks.length === 0 && artifacts.length === 0 && (
          <div className="bg-surface border border-line rounded-xl p-6 text-center text-xs text-muted">
            No execution trace steps recorded for this query.
          </div>
        )}
      </div>
    </div>
  );
}
