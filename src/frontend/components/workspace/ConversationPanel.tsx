"use client";

import React, { useRef, useEffect } from "react";
import { Sparkles, MessageSquare, ArrowRight } from "lucide-react";
import { WorkspaceMessage } from "@/hooks/useWorkspace";
import { useLanguage } from "@/context/LanguageContext";
import { MessageItem } from "./MessageItem";
import { QueryComposer } from "./QueryComposer";
import { ClarificationChips } from "./ClarificationChips";
import { HITLApprovalBanner } from "./HITLApprovalBanner";

interface ConversationPanelProps {
  messages: WorkspaceMessage[];
  isLoading: boolean;
  isApproving: boolean;
  onSubmitQuery: (question: string) => void;
  onApproveHitl: (approved: boolean, reason?: string) => void;
  onSelectOption: (option: string) => void;
  onResetConversation: () => void;
}

const samplePromptsEn = [
  "Which 10 products generated the most revenue in 2003?",
  "Compare monthly sales between store channel and web channel in 2002.",
  "Which customer income demographics show the highest item return rate?",
];

const samplePromptsVi = [
  "10 sản phẩm nào mang lại doanh thu cao nhất năm 2003?",
  "So sánh doanh số hàng tháng giữa kênh cửa hàng và kênh web năm 2002.",
  "Phân khúc thu nhập khách hàng nào có tỷ lệ trả hàng cao nhất?",
];

export function ConversationPanel({
  messages,
  isLoading,
  isApproving,
  onSubmitQuery,
  onApproveHitl,
  onSelectOption,
  onResetConversation,
}: ConversationPanelProps) {
  const { t, locale } = useLanguage();
  const scrollRef = useRef<HTMLDivElement>(null);
  const samplePrompts = locale === "vi" ? samplePromptsVi : samplePromptsEn;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading, isApproving]);

  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
  const isClarificationNeeded =
    lastAssistantMsg?.status === "CLARIFICATION_REQUIRED" &&
    lastAssistantMsg.queryResponse?.suggested_options &&
    lastAssistantMsg.queryResponse.suggested_options.length > 0;

  const isHitlNeeded =
    lastAssistantMsg?.status === "PENDING_APPROVAL" ||
    !!lastAssistantMsg?.queryResponse?.requires_hitl;

  return (
    <section className="bg-surface border border-line rounded-xl shadow-panel flex flex-col overflow-hidden h-full min-h-[550px]">
      {/* Panel Header */}
      <div className="p-3.5 md:p-4 border-b border-line flex items-center justify-between gap-3 bg-surface shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary-soft text-primary grid place-items-center shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <strong className="block text-xs font-bold text-foreground">
              {t("workspace.conversationThread")}
            </strong>
            <small className="block text-[10px] text-muted">
              {t("workspace.activeSession")}
            </small>
          </div>
        </div>

        <button
          type="button"
          onClick={onResetConversation}
          className="text-[11px] text-primary hover:underline font-bold"
        >
          {t("workspace.newConversation")}
        </button>
      </div>

      {/* Message Feed Scroll Area */}
      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col justify-center py-6 space-y-4">
            <div className="text-center space-y-2">
              <div className="w-10 h-10 rounded-xl bg-primary-soft text-primary grid place-items-center mx-auto shadow-sm">
                <MessageSquare className="w-5 h-5" />
              </div>
              <h2 className="text-sm font-bold text-foreground">
                {t("workspace.emptyPromptTitle")}
              </h2>
              <p className="text-xs text-muted max-w-sm mx-auto leading-relaxed">
                {t("workspace.emptyPromptDesc")}
              </p>
            </div>

            <div className="space-y-2 pt-2">
              <span className="text-[10px] uppercase font-bold tracking-wider text-faint block">
                {t("workspace.suggestedPrompts")}
              </span>
              {samplePrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSubmitQuery(prompt)}
                  className="w-full text-left p-2.5 rounded-lg border border-line hover:border-primary/40 bg-surface-2 hover:bg-surface text-xs text-foreground transition flex items-center justify-between gap-2 shadow-sm group"
                >
                  <span className="truncate">{prompt}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-faint group-hover:text-primary shrink-0" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="text-center text-[10px] uppercase font-bold tracking-wider text-faint">
              {t("workspace.sessionActivity")}
            </div>

            {messages.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))}

            {isClarificationNeeded && (
              <ClarificationChips
                question={
                  lastAssistantMsg.queryResponse?.clarification_question ||
                  t("workspace.clarificationTitle")
                }
                options={lastAssistantMsg.queryResponse!.suggested_options!}
                onSelectOption={onSelectOption}
              />
            )}

            {isHitlNeeded && (
              <HITLApprovalBanner
                estimatedCostBytes={lastAssistantMsg.queryResponse?.estimated_cost_bytes}
                sql={lastAssistantMsg.queryResponse?.sql}
                onApprove={onApproveHitl}
                isApproving={isApproving}
              />
            )}
          </>
        )}
      </div>

      {/* Query Composer Form */}
      <QueryComposer onSubmit={onSubmitQuery} isLoading={isLoading} />
    </section>
  );
}
