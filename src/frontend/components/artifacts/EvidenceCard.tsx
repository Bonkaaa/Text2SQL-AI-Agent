"use client";

import React, { useState } from "react";
import { FileCheck, ChevronDown, ChevronUp, Code2 } from "lucide-react";
import type { EvidenceArtifact } from "../../types/artifacts";

interface EvidenceCardProps {
  artifact: EvidenceArtifact;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ artifact }) => {
  const [showSql, setShowSql] = useState(false);

  return (
    <div className="rounded-xl border border-border-default/80 bg-surface-secondary/70 p-4 space-y-3 backdrop-blur-md shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-primary-500/10 text-primary-400">
            <FileCheck className="w-4 h-4" />
          </div>
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Bằng chứng định lượng
          </span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono-data bg-slate-800 text-slate-400 border border-slate-700/60">
            {artifact.task_id}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setShowSql((prev) => !prev)}
          className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-200 transition-colors"
          aria-label={showSql ? "Ẩn câu SQL" : "Xem câu SQL"}
        >
          <Code2 className="w-3.5 h-3.5" />
          <span>{showSql ? "Ẩn SQL" : "Xem SQL"}</span>
          {showSql ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* Claim / Statement */}
      <p className="text-xs font-medium text-slate-200 leading-relaxed">
        {artifact.claim}
      </p>

      {/* Collapsible SQL Block */}
      {showSql && (
        <div className="rounded-lg bg-surface-primary/90 border border-border-default/80 p-3 font-mono text-[11px] text-slate-300 overflow-x-auto custom-scrollbar">
          <pre className="whitespace-pre-wrap">{artifact.supporting_sql}</pre>
        </div>
      )}

      {/* Sample Values Table (nếu có) */}
      {artifact.sample_values && artifact.sample_values.length > 0 && (
        <div className="rounded-lg border border-border-default/60 overflow-hidden bg-surface-primary/40 text-[11px]">
          <div className="px-3 py-1.5 bg-surface-primary/80 border-b border-border-default/60 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Mẫu số liệu kiểm chứng
          </div>
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border-default/40 text-slate-400">
                  {Object.keys(artifact.sample_values[0]).map((key) => (
                    <th key={key} className="py-1 px-3 font-medium">
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default/30">
                {artifact.sample_values.map((val, idx) => (
                  <tr key={idx} className="hover:bg-surface-secondary/30">
                    {Object.keys(val).map((k) => (
                      <td key={k} className="py-1 px-3 font-mono-data tabular-nums text-slate-300">
                        {String(val[k])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
