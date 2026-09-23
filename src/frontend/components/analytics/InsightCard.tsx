"use client";

import React, { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Lightbulb,
  Clock,
  Copy,
  Check,
  Sparkles,
  BarChart3,
  Code2,
} from "lucide-react";
import { RechartsConfig } from "@/types/api";
import { formatDurationSeconds } from "@/utils/formatters";
import {
  alignDataWithConfig,
  extractRechartsConfig,
  parseMarkdownTable,
} from "@/utils/markdownChartParser";
import { DynamicChart } from "./DynamicChart";

export interface InsightCardProps {
  insightText: string;
  title?: string;
  subtitle?: string;
  executionTimeMs?: number;
  data?: Record<string, any>[];
  className?: string;
  onCopy?: () => void;
}

export function InsightCard({
  insightText,
  title = "Nhận định kinh doanh",
  subtitle = "Tổng hợp từ dữ liệu TPC-H",
  executionTimeMs,
  data: externalData,
  className = "",
  onCopy,
}: InsightCardProps) {
  const [copied, setCopied] = useState(false);
  const [showRawJsonMap, setShowRawJsonMap] = useState<Record<string, boolean>>({});

  const handleCopy = async () => {
    onCopy?.();
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(insightText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Bỏ qua lỗi trong môi trường clipboard bị giới hạn
    }
  };

  // Trích xuất sẵn dữ liệu bảng từ Markdown (nếu không có externalData truyền vào)
  const parsedTableData = useMemo(() => {
    if (externalData && externalData.length > 0) {
      return externalData;
    }
    return parseMarkdownTable(insightText).data;
  }, [externalData, insightText]);

  // Bộ renderer tùy chỉnh cho ReactMarkdown
  const markdownComponents = useMemo(
    () => ({
      // 1. Tiêu đề (Headings)
      h1: ({ children, ...props }: any) => (
        <h3
          className="text-sm font-bold text-amber-200 mt-4 mb-2 flex items-center gap-1.5 border-b border-surface-border pb-1.5 tracking-wide uppercase"
          {...props}
        >
          {children}
        </h3>
      ),
      h2: ({ children, ...props }: any) => (
        <h4
          className="text-xs font-bold text-amber-300 mt-3 mb-2 flex items-center gap-1.5 border-b border-surface-border/60 pb-1 uppercase tracking-wide"
          {...props}
        >
          {children}
        </h4>
      ),
      h3: ({ children, ...props }: any) => (
        <h4
          className="text-xs font-bold text-amber-300 mt-3 mb-1.5 flex items-center gap-1.5 tracking-wide"
          {...props}
        >
          {children}
        </h4>
      ),
      h4: ({ children, ...props }: any) => (
        <h5
          className="text-xs font-semibold text-slate-200 mt-2.5 mb-1"
          {...props}
        >
          {children}
        </h5>
      ),

      // 2. Đoạn văn (Paragraphs)
      p: ({ children, ...props }: any) => (
        <p className="text-xs text-slate-200 leading-relaxed my-1.5" {...props}>
          {children}
        </p>
      ),

      // 3. In đậm (Strong)
      strong: ({ children, ...props }: any) => (
        <strong
          className="font-semibold text-amber-200 bg-amber-500/10 px-1 py-0.5 rounded border border-amber-500/20"
          {...props}
        >
          {children}
        </strong>
      ),

      // 4. Danh sách (Lists)
      ul: ({ children, ...props }: any) => (
        <ul className="my-2 space-y-1.5 pl-4 list-disc text-xs text-slate-200 marker:text-amber-400" {...props}>
          {children}
        </ul>
      ),
      ol: ({ children, ...props }: any) => (
        <ol className="my-2 space-y-1.5 pl-4 list-decimal text-xs text-slate-200 marker:text-amber-400 font-medium" {...props}>
          {children}
        </ol>
      ),
      li: ({ children, ...props }: any) => (
        <li className="leading-relaxed pl-1" {...props}>
          {children}
        </li>
      ),

      // 5. Đường kẻ phân tách (HR)
      hr: ({ ...props }: any) => (
        <hr className="my-4 border-surface-border/60" {...props} />
      ),

      // 6. Bảng dữ liệu (Tables)
      table: ({ children, ...props }: any) => (
        <div className="overflow-x-auto my-3.5 rounded-xl border border-surface-border bg-[#0a0f1d]/80 shadow-md">
          <table className="w-full text-left text-xs border-collapse" {...props}>
            {children}
          </table>
        </div>
      ),
      thead: ({ children, ...props }: any) => (
        <thead className="bg-surface-subtle/90 border-b border-surface-border text-slate-200 uppercase text-[11px] font-semibold tracking-wider" {...props}>
          {children}
        </thead>
      ),
      th: ({ children, ...props }: any) => (
        <th className="px-3.5 py-2.5 whitespace-nowrap text-left border-r border-surface-border/40 last:border-r-0 text-slate-200 font-semibold" {...props}>
          {children}
        </th>
      ),
      tbody: ({ children, ...props }: any) => (
        <tbody className="divide-y divide-surface-border/30" {...props}>
          {children}
        </tbody>
      ),
      tr: ({ children, ...props }: any) => (
        <tr className="hover:bg-brand-500/10 transition-colors even:bg-white/[0.02]" {...props}>
          {children}
        </tr>
      ),
      td: ({ children, ...props }: any) => (
        <td className="px-3.5 py-2 text-slate-300 border-r border-surface-border/20 last:border-r-0 whitespace-nowrap text-xs font-mono" {...props}>
          {children}
        </td>
      ),

      // 7. Khối mã lệnh & Trực quan hóa Biểu đồ (Code & Dynamic Chart)
      code: ({ node, inline, className: codeClassName, children, ...props }: any) => {
        const codeContent = String(children).replace(/\n$/, "");
        const isJson =
          codeClassName?.includes("language-json") ||
          codeContent.trim().startsWith("{");

        // Nếu là inline code: hiển thị badge font-mono
        if (inline) {
          return (
            <code
              className="text-[11px] font-mono text-brand-300 bg-surface-subtle px-1.5 py-0.5 rounded border border-surface-border"
              {...props}
            >
              {children}
            </code>
          );
        }

        // Kiểm tra xem đoạn code này có phải cấu hình Recharts JSON không
        if (isJson) {
          const config: RechartsConfig | null = extractRechartsConfig(codeContent);

          if (config) {
            const blockId = `chart_${config.title || config.chart_type}_${codeContent.length}`;
            const isRawVisible = !!showRawJsonMap[blockId];

            // Căn chỉnh dữ liệu bảng với config
            const alignedData = alignDataWithConfig(parsedTableData, config);

            return (
              <div className="my-3 space-y-2">
                {/* Thanh điều khiển phụ: Chuyển đổi Biểu đồ / JSON thô */}
                <div className="flex items-center justify-between px-1 text-[11px]">
                  <span className="flex items-center gap-1.5 text-indigo-300 font-medium">
                    <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Biểu đồ trực quan ({config.chart_type.toUpperCase()})</span>
                  </span>

                  <button
                    type="button"
                    onClick={() =>
                      setShowRawJsonMap((prev) => ({
                        ...prev,
                        [blockId]: !prev[blockId],
                      }))
                    }
                    className="flex items-center gap-1 px-2 py-0.5 rounded bg-surface-subtle hover:bg-surface-subtle/80 text-slate-400 hover:text-slate-200 border border-surface-border transition-colors text-[10px]"
                  >
                    <Code2 className="w-3 h-3" />
                    <span>{isRawVisible ? "Ẩn JSON" : "Xem JSON cấu hình"}</span>
                  </button>
                </div>

                {/* Render DynamicChart Component */}
                <div className="rounded-xl border border-surface-border bg-[#080d19]/90 p-2 shadow-inner">
                  <DynamicChart config={config} data={alignedData} height={300} />
                </div>

                {/* Khi người dùng muốn xem raw JSON cấu hình */}
                {isRawVisible && (
                  <div className="relative mt-2">
                    <pre className="p-3 rounded-lg bg-surface-subtle/80 border border-surface-border text-[11px] font-mono text-slate-300 overflow-x-auto">
                      <code>{codeContent}</code>
                    </pre>
                  </div>
                )}
              </div>
            );
          }
        }

        // Code block thông thường
        return (
          <div className="my-2 relative rounded-lg border border-surface-border bg-[#080d19]/90 p-3 overflow-x-auto">
            <pre className="text-xs font-mono text-slate-200">
              <code {...props}>{children}</code>
            </pre>
          </div>
        );
      },
    }),
    [parsedTableData, showRawJsonMap]
  );

  return (
    <div
      className={`rounded-2xl border border-brand-500/25 bg-gradient-to-br from-[#0c1322]/90 via-[#0a0f1d]/90 to-[#070b14]/90 p-4 sm:p-5 space-y-3.5 backdrop-blur-md shadow-card transition-all ${className}`}
      role="region"
      aria-label="Thẻ tóm tắt nhận định kinh doanh"
    >
      {/* Header Bar */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
            <Lightbulb className="w-4 h-4 text-amber-400" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-amber-200 tracking-wide uppercase flex items-center gap-1.5">
              <span>{title}</span>
              <Sparkles className="w-3 h-3 text-amber-400" />
            </h4>
            <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>
          </div>
        </div>

        {/* Badges & Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          {executionTimeMs !== undefined && (
            <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-surface-subtle border border-surface-border text-slate-300 font-mono flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-400" />
              <span>{formatDurationSeconds(executionTimeMs)}</span>
            </span>
          )}

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-subtle hover:bg-surface-subtle/80 text-slate-300 hover:text-white transition-colors border border-surface-border text-xs font-medium"
            aria-label={copied ? "Đã chép" : "Sao chép"}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-semibold">Đã chép</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-400" />
                <span>Sao chép</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Insight Content Body - Compiled Markdown */}
      <div className="text-xs text-slate-200 leading-relaxed bg-surface/40 p-3.5 sm:p-4 rounded-xl border border-surface-border">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {insightText}
        </ReactMarkdown>
      </div>
    </div>
  );
}

export default InsightCard;
