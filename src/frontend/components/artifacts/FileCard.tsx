"use client";

import React from "react";
import { FileSpreadsheet, Download } from "lucide-react";
import type { FileArtifact } from "../../types/artifacts";

interface FileCardProps {
  artifact: FileArtifact;
}

export const FileCard: React.FC<FileCardProps> = ({ artifact }) => {
  return (
    <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-border-default/80 bg-surface-secondary/70 backdrop-blur-md">
      <div className="flex items-center gap-2.5">
        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
          <FileSpreadsheet className="w-4 h-4" />
        </div>
        <div>
          <span className="text-xs font-medium text-slate-200 block truncate max-w-xs sm:max-w-md">
            {artifact.file_name}
          </span>
          <span className="text-[10px] text-slate-400 uppercase font-mono-data">
            {artifact.file_type}
          </span>
        </div>
      </div>

      <a
        href={artifact.download_url}
        download={artifact.file_name}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 bg-surface-primary hover:bg-surface-primary/80 border border-border-default transition-all"
        aria-label={`Tải xuống ${artifact.file_name}`}
      >
        <Download className="w-3.5 h-3.5 text-primary-400" />
        <span className="hidden sm:inline">Tải xuống</span>
      </a>
    </div>
  );
};
