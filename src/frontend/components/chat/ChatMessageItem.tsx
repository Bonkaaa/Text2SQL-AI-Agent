"use client";

import React, { useMemo, useState } from "react";
import {
  BarChart3,
  Clock,
  Database,
  Sparkles,
  User,
} from "lucide-react";
import { ChatMessage, QueryResponse } from "@/types/api";
import { ReasoningTimeline } from "@/components/chat/ReasoningTimeline";
import { ExecutionStepper } from "@/components/chat/ExecutionStepper";
import { LoadingSkeleton } from "@/components/chat/LoadingSkeleton";
import { ClarificationCard } from "@/components/chat/ClarificationCard";
import { HITLApprovalCard } from "@/components/chat/HITLApprovalCard";
import { ErrorFeedbackCard } from "@/components/chat/ErrorFeedbackCard";
import { InsightCard } from "@/components/analytics/InsightCard";
import { DynamicChart } from "@/components/analytics/DynamicChart";
import { DataTable } from "@/components/analytics/DataTable";
import { SQLViewer } from "@/components/analytics/SQLViewer";
import { formatDurationSeconds } from "@/utils/formatters";
import { extractChartAndDataFromMarkdown } from "@/utils/markdownChartParser";
import { ArtifactRenderer } from "@/components/artifacts/ArtifactRenderer";
import { extractArtifactsFromResponse } from "@/utils/artifactAdapter";
import { TrustBadges } from "@/components/chat/TrustBadges";

export interface ChatMessageItemProps {
  message: ChatMessage;
  isGlobalLoading?: boolean;
  isApprovingHitl?: boolean;
  onApproveHitl?: (approved: boolean, reason?: string) => void;
  onSelectOption?: (option: string) => void;
  onRetry?: () => void;
}

export function ChatMessageItem({
  message,
  isGlobalLoading = false,
  isApprovingHitl = false,
  onApproveHitl,
  onSelectOption,
  onRetry,
}: ChatMessageItemProps) {
  const isUser = message.role === "user";
  const response: QueryResponse | undefined = message.queryResponse;

  // Bổ trợ trích xuất cấu hình Chart và Data từ Markdown nếu backend chưa gửi trực tiếp
  const extractedMarkdownInfo = useMemo(() => {
    if (!response?.final_answer) return null;
    return extractChartAndDataFromMarkdown(response.final_answer);
  }, [response?.final_answer]);

  const effectiveRechartsConfig =
    response?.recharts_config || extractedMarkdownInfo?.config || null;
  const effectiveData =
    response?.data && response.data.length > 0
      ? response.data
      : extractedMarkdownInfo?.data || [];
  const effectiveColumns =
    response?.columns && response.columns.length > 0
      ? response.columns
      : extractedMarkdownInfo?.columns || [];

  const hasChart = !!(
    effectiveRechartsConfig &&
    effectiveData &&
    effectiveData.length > 0
  );
  const hasData = effectiveData.length > 0;
  const totalRows = effectiveData.length;

  const [activeTab, setActiveTab] = useState<"chart" | "table" | "sql">(
    hasChart ? "chart" : "table"
  );

  // 1. Tin nhắn của Người dùng (User Message)
  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-2.5 my-3 animate-in fade-in duration-200">
        <div className="max-w-xl bg-blue-600/75 hover:bg-blue-600/85 text-white rounded-2xl rounded-tr-xs px-4 py-2.5 shadow-sm border border-blue-500/30 transition-colors">
          <p className="text-sm leading-relaxed whitespace-pre-wrap font-sans-ui">{message.content}</p>
          <div className="text-[10px] text-blue-200/70 mt-1 text-right font-mono">
            {new Date(message.timestamp).toLocaleTimeString("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
        <div className="w-8 h-8 rounded-xl bg-surface-secondary border border-surface-border flex items-center justify-center text-blue-400 flex-shrink-0 shadow-sm mt-0.5">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // 2. Tin nhắn Bot đang xử lý suy luận (Loading State)
  if (message.isLoading) {
    return (
      <div className="flex items-start gap-3 my-4 animate-in fade-in duration-200">
        <div className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
          <Sparkles className="w-4 h-4 animate-pulse" />
        </div>
        <div className="glass-card rounded-2xl rounded-tl-sm p-4 sm:p-5 w-full max-w-3xl border border-surface-border space-y-4 shadow-card">
          <ExecutionStepper isLoading={true} />
          <LoadingSkeleton />
          <div className="pt-2 border-t border-surface-border/50">
            <ReasoningTimeline isLoading={true} currentStep={2} />
          </div>
        </div>
      </div>
    );
  }

  // 3. Tin nhắn Bot đã phản hồi (Assistant Response)
  const isClarification =
    response?.status === "CLARIFICATION_REQUIRED" ||
    (response?.is_ambiguous && (response?.suggested_options?.length || 0) > 0);

  const isPendingApproval =
    (response?.requires_hitl || response?.status === "PENDING_APPROVAL") &&
    response?.status !== "COMPLETED";

  const isError =
    !!(response?.error ||
    response?.status === "ERROR" ||
    response?.status === "EXECUTION_FAILED");

  return (
    <div className="flex items-start gap-3 my-5 animate-in fade-in duration-200">
      {/* Bot Avatar */}
      <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 text-white flex items-center justify-center flex-shrink-0 shadow-glow mt-1">
        <Sparkles className="w-4 h-4" />
      </div>

      <div className="glass-card rounded-2xl rounded-tl-sm p-4 sm:p-5 w-full max-w-3xl border border-surface-border space-y-4 shadow-card">
        {/* Header Bar: Metadata & Enterprise Trust Badges */}
        <div className="flex items-center justify-between border-b border-surface-border pb-2.5 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-200">DeepAgents TPC-DS</span>
            {!isError && (
              <TrustBadges
                astVerified={Boolean((response as any)?.ast_verified || (response as any)?.metadata?.ast_verified)}
                rbacEnforced={Boolean((response as any)?.rbac_enforced || (response as any)?.metadata?.rbac_enforced)}
                role={(response as any)?.role || (response as any)?.metadata?.role}
                piiProtected={Boolean((response as any)?.pii_masked || (response as any)?.metadata?.pii_masked)}
              />
            )}
          </div>

          <div className="flex items-center gap-3 text-[11px] text-slate-400">
            {!isError && response?.execution_time_ms !== undefined && response.execution_time_ms > 0 && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />
                <span>{formatDurationSeconds(response.execution_time_ms)}</span>
              </span>
            )}
            {!isError && hasData && (
              <span className="flex items-center gap-1 font-mono">
                <Database className="w-3 h-3 text-emerald-400" />
                <span>{totalRows} bản ghi</span>
              </span>
            )}
          </div>
        </div>

        {/* 1. Authentic Live Execution Stepper (Telemetry) */}
        {!isError && (
          <ExecutionStepper
            executionTimeMs={response?.execution_time_ms}
            totalRows={totalRows}
          />
        )}

        {/* 1b. Reasoning CoT Timeline */}
        {!isError && (
          <ReasoningTimeline
            executionTimeMs={response?.execution_time_ms}
            defaultExpanded={false}
          />
        )}

        {/* 2. Trạng thái YÊU CẦU LÀM RÕ (CLARIFICATION_REQUIRED) */}
        {isClarification && (
          <ClarificationCard
            question={
              response?.clarification_question ||
              response?.final_answer ||
              response?.question
            }
            options={response?.suggested_options}
            disabled={isGlobalLoading || message.isLoading}
            onSelectOption={onSelectOption || (() => {})}
          />
        )}

        {/* 3. Trạng thái CHỜ DUYỆT HITL (PENDING_APPROVAL) */}
        {isPendingApproval && (
          <HITLApprovalCard
            sql={response?.sql}
            estimatedBytes={response?.estimated_cost_bytes}
            isSubmitting={isApprovingHitl}
            onApprove={() => onApproveHitl?.(true)}
            onReject={(reason) => onApproveHitl?.(false, reason)}
          />
        )}

        {/* 4. Trạng thái THÔNG BÁO LỖI (ERROR / EXECUTION_FAILED) */}
        {isError && (
          <ErrorFeedbackCard
            errorMessage={
              response?.error ||
              "Đã xảy ra sự cố trong quá trình xử lý hoặc thẩm định an toàn"
            }
            errorType={response?.error_type || undefined}
            retryCount={response?.retry_count || undefined}
            onRetry={onRetry}
          />
        )}

        {/* 5. Trạng thái HOÀN TẤT THÀNH CÔNG (COMPLETED) */}
        {!isClarification && !isPendingApproval && !isError && response && (
          <>
            {/* Phân nhánh A: Kiến trúc đa Artifacts mới (Multi-Artifact Orchestration Engine) */}
            {(response.response_package || (response.output_artifacts && response.output_artifacts.length > 0)) ? (
              <div className="space-y-4">
                {(() => {
                  const extracted = extractArtifactsFromResponse(response);
                  return (
                    <ArtifactRenderer
                      artifacts={extracted.artifacts}
                      layout={extracted.layout}
                      directAnswer={extracted.directAnswer}
                      detailedInsight={extracted.detailedInsight}
                    />
                  );
                })()}

                {/* SQL Code Block nếu có query */}
                {response.sql && (
                  <div className="pt-2">
                    <SQLViewer sql={response.sql} />
                  </div>
                )}
              </div>
            ) : (
              /* Phân nhánh B: Hiển thị tab truyền thống (Legacy fallback) */
              <>
                {/* Business Insight Card */}
                {response.final_answer && (
                  <InsightCard
                    insightText={response.final_answer}
                    executionTimeMs={response.execution_time_ms}
                    data={effectiveData}
                  />
                )}

                {/* Tab Switcher: Dynamic Chart vs Data Table vs SQL Code */}
                {(hasChart || hasData || !!response.sql) && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between border-b border-surface-border pb-2">
                      <div className="flex items-center gap-2">
                        {hasChart && (
                          <button
                            onClick={() => setActiveTab("chart")}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                              activeTab === "chart"
                                ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                                : "text-slate-400 hover:text-slate-200"
                            }`}
                          >
                            <BarChart3 className="w-3.5 h-3.5" />
                            <span>Biểu đồ</span>
                          </button>
                        )}
                        {hasData && (
                          <button
                            onClick={() => setActiveTab("table")}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                              activeTab === "table"
                                ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                                : "text-slate-400 hover:text-slate-200"
                            }`}
                          >
                            Bảng kết quả
                          </button>
                        )}
                        {response.sql && (
                          <button
                            onClick={() => setActiveTab("sql")}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                              activeTab === "sql" || (!hasData && !hasChart)
                                ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                                : "text-slate-400 hover:text-slate-200"
                            }`}
                          >
                            Truy vấn SQL
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Content: Dynamic Chart View */}
                    {activeTab === "chart" && hasChart && effectiveRechartsConfig && (
                      <DynamicChart
                        config={effectiveRechartsConfig}
                        data={effectiveData}
                      />
                    )}

                    {/* Content: Data Table View */}
                    {activeTab === "table" && hasData && (
                      <DataTable
                        columns={
                          effectiveColumns.length > 0
                            ? effectiveColumns
                            : Object.keys(effectiveData[0] || {})
                        }
                        data={effectiveData}
                        tableName={`query_result_${response.session_id || ""}`}
                      />
                    )}

                    {/* Content: SQL View */}
                    {activeTab === "sql" && response.sql && (
                      <SQLViewer sql={response.sql} />
                    )}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Alias export to satisfy Component 5.1/5.3 specification
export { ChatMessageItem as MessageItem };
